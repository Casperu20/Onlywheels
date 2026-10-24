from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import TimeStampedModel
from apps.fitment.normalize import format_tire_size, normalize_pcd, normalize_thread


class ProductType(models.TextChoices):
    WHEEL = "wheel", "Wheel"
    TIRE = "tire", "Tire"
    SET = "set", "Complete wheel set"
    ACCESSORY = "accessory", "Accessory"


class Finish(models.TextChoices):
    SILVER = "silver", "Silver"
    BLACK = "black", "Black"
    BRONZE = "bronze", "Bronze"
    GUNMETAL = "gunmetal", "Gunmetal"
    CHROME = "chrome", "Chrome"
    WHITE = "white", "White"


class Season(models.TextChoices):
    SUMMER = "summer", "Summer"
    WINTER = "winter", "Winter"
    ALL_SEASON = "all_season", "All season"


class Brand(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    logo = models.ImageField(upload_to="brands/", blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    product_type = models.CharField(max_length=20, choices=ProductType.choices)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "name")
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    type = models.CharField(max_length=20, choices=ProductType.choices)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    style = models.CharField(max_length=60, blank=True, help_text="e.g. multi-spoke, mesh, Y-spoke")
    description = models.TextField(blank=True)
    badge = models.CharField(max_length=40, blank=True, help_text='Short label, e.g. "Bestseller"')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    # Denormalized, updated by the reviews app.
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    history = HistoricalRecords()

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=["type", "is_active"])]

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class ProductVariant(TimeStampedModel):
    """A purchasable SKU. Which spec fields are used depends on the product type."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField("SKU", max_length=64, unique=True)
    label = models.CharField(max_length=120, blank=True, help_text="Free text, mainly for accessories")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="RON, VAT included")
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Wheels and sets
    finish = models.CharField(max_length=20, choices=Finish.choices, blank=True)
    diameter_in = models.PositiveSmallIntegerField("Diameter (in)", null=True, blank=True)
    width_in = models.DecimalField("Width (J)", max_digits=3, decimal_places=1, null=True, blank=True)
    et_mm = models.SmallIntegerField("ET / offset (mm)", null=True, blank=True)
    pcd = models.CharField("PCD", max_length=20, blank=True)
    center_bore_mm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # Tires and sets
    tire_width_mm = models.PositiveSmallIntegerField(null=True, blank=True)
    tire_aspect = models.PositiveSmallIntegerField(null=True, blank=True)
    load_index = models.PositiveSmallIntegerField(null=True, blank=True)
    speed_rating = models.CharField(max_length=2, blank=True)
    season = models.CharField(max_length=20, choices=Season.choices, blank=True)
    tire_size = models.CharField(max_length=20, blank=True, editable=False, db_index=True)

    # Accessories (lug nuts/bolts)
    thread_size = models.CharField(max_length=20, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ("price",)
        indexes = [
            models.Index(fields=["pcd"]),
            models.Index(fields=["diameter_in"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="variant_price_gte_0"),
        ]

    def __str__(self) -> str:
        return f"{self.product} [{self.sku}]"

    def summary(self) -> str:
        """Short spec line, e.g. 19" · 8.5J · 5x112 · ET35 (same format as the frontend)."""
        product_type = self.product.type
        if product_type == ProductType.ACCESSORY:
            return self.label
        load = f"{self.load_index}{self.speed_rating}" if self.load_index else ""
        tire = " ".join(part for part in (self.tire_size, load) if part)
        if product_type == ProductType.TIRE:
            return tire
        wheel = " · ".join(
            part
            for part in (
                f'{self.diameter_in}"' if self.diameter_in else "",
                f"{format(self.width_in.normalize(), 'f')}J" if self.width_in is not None else "",
                self.pcd,
                f"ET{self.et_mm}" if self.et_mm is not None else "",
            )
            if part
        )
        return f"{wheel} · {self.tire_size}" if product_type == ProductType.SET and self.tire_size else wheel

    def clean(self) -> None:
        if self.pcd:
            try:
                self.pcd = normalize_pcd(self.pcd)
            except ValueError as exc:
                raise ValidationError({"pcd": str(exc)}) from exc
        product_type = self.product.type if self.product_id else None
        if product_type in (ProductType.WHEEL, ProductType.SET):
            missing = [
                f
                for f in ("diameter_in", "width_in", "et_mm", "pcd", "center_bore_mm")
                if getattr(self, f) in (None, "")
            ]
            if missing:
                raise ValidationError({f: "Required for wheels and sets." for f in missing})
        if product_type == ProductType.TIRE:
            missing = [
                f
                for f in ("tire_width_mm", "tire_aspect", "diameter_in")
                if getattr(self, f) is None
            ]
            if missing:
                raise ValidationError({f: "Required for tires." for f in missing})

    def save(self, *args, **kwargs):
        if self.pcd:
            self.pcd = normalize_pcd(self.pcd)
        if self.thread_size:
            self.thread_size = normalize_thread(self.thread_size)
        if self.tire_width_mm and self.tire_aspect and self.diameter_in:
            self.tire_size = format_tire_size(self.tire_width_mm, self.tire_aspect, self.diameter_in)
        else:
            self.tire_size = ""
        super().save(*args, **kwargs)


class ProductMedia(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=150, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "created_at")
        verbose_name_plural = "product media"

    def __str__(self) -> str:
        return self.alt or self.image.name
