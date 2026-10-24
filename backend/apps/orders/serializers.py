from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.appointments.models import Appointment
from apps.garages.models import Garage

from .models import Order, OrderItem, OrderStatusChange


class QuoteRequestSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=Order.Delivery.choices)
    garage_id = serializers.PrimaryKeyRelatedField(
        queryset=Garage.objects.filter(is_active=True),
        source="garage",
        required=False,
        allow_null=True,
    )
    voucher_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["delivery_method"] == Order.Delivery.GARAGE_FITTING and not attrs.get("garage"):
            raise serializers.ValidationError({"garage_id": ["Choose a partner garage."]})
        return attrs


class CheckoutSerializer(QuoteRequestSerializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r"^\+?[0-9 ]{9,16}$", max_length=32)
    line1 = serializers.CharField(max_length=255)
    line2 = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    city = serializers.CharField(max_length=100)
    county = serializers.CharField(max_length=100)
    postal_code = serializers.RegexField(r"^[0-9]{6}$", max_length=10)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    slot_start = serializers.DateTimeField(required=False, allow_null=True)
    accept_terms = serializers.BooleanField()

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs["delivery_method"] == Order.Delivery.GARAGE_FITTING and not attrs.get("slot_start"):
            raise serializers.ValidationError({"slot_start": ["Choose a fitting time slot."]})
        return attrs


class QuoteSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping = serializers.DecimalField(max_digits=12, decimal_places=2)
    fitting = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat = serializers.DecimalField(max_digits=12, decimal_places=2)
    voucher_code = serializers.CharField(allow_null=True)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "product_slug",
            "product_type",
            "sku",
            "description",
            "unit_price",
            "quantity",
            "line_total",
        )


class AppointmentGarageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Garage
        fields = ("name", "slug", "city", "address", "phone")


class AppointmentSerializer(serializers.ModelSerializer):
    garage = AppointmentGarageSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = ("garage", "slot_start", "slot_end", "status")


class StatusChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusChange
        fields = ("status", "note", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "number",
            "status",
            "delivery_method",
            "total",
            "currency",
            "item_count",
            "created_at",
            "paid_at",
            "reserved_until",
            "can_pay",
            "can_cancel",
        )

    def get_item_count(self, obj: Order) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_can_pay(self, obj: Order) -> bool:
        return obj.status == Order.Status.PENDING_PAYMENT and bool(
            obj.reserved_until and obj.reserved_until > timezone.now()
        )

    def get_can_cancel(self, obj: Order) -> bool:
        return obj.status == Order.Status.PENDING_PAYMENT


class OrderDetailSerializer(OrderSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    appointment = serializers.SerializerMethodField()
    status_changes = StatusChangeSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = (
            *OrderSerializer.Meta.fields,
            "email",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "county",
            "postal_code",
            "notes",
            "subtotal",
            "discount",
            "shipping",
            "fitting",
            "vat",
            "voucher_code",
            "items",
            "appointment",
            "status_changes",
        )

    @staticmethod
    def _appointment(obj: Order) -> Appointment | None:
        try:
            return obj.appointment
        except Appointment.DoesNotExist:
            return None

    @extend_schema_field(AppointmentSerializer(allow_null=True))
    def get_appointment(self, obj: Order):
        appointment = self._appointment(obj)
        return AppointmentSerializer(appointment).data if appointment else None


class CheckoutSessionSerializer(serializers.Serializer):
    checkout_url = serializers.URLField()
