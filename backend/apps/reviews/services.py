from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

from .models import Review

PURCHASED_STATUSES = (
    Order.Status.PAID,
    Order.Status.PROCESSING,
    Order.Status.SHIPPED,
    Order.Status.READY_FOR_FITTING,
    Order.Status.COMPLETED,
)


def has_purchased(user, product: Product) -> bool:
    return OrderItem.objects.filter(
        order__user=user, order__status__in=PURCHASED_STATUSES, variant__product=product
    ).exists()


def create_review(user, product: Product, *, rating: int, title: str = "", body: str = "") -> Review:
    return Review.objects.create(
        user=user,
        product=product,
        rating=rating,
        title=title,
        body=body,
        is_verified_purchase=has_purchased(user, product),
    )


def recalculate_rating(product: Product) -> None:
    stats = product.reviews.filter(status=Review.Status.APPROVED).aggregate(avg=Avg("rating"), count=Count("id"))
    product.rating_avg = Decimal(stats["avg"] or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    product.rating_count = stats["count"]
    product.save(update_fields=["rating_avg", "rating_count", "updated_at"])


@transaction.atomic
def moderate(review: Review, status: str) -> None:
    review.status = status
    review.save(update_fields=["status", "updated_at"])
    recalculate_rating(review.product)
