from collections import Counter
from datetime import date, datetime, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.garages.models import Garage

from .models import Appointment


def booking_window(now: datetime | None = None) -> tuple[datetime, date]:
    """Earliest bookable moment and last bookable day."""
    now = now or timezone.now()
    earliest = now + timedelta(hours=settings.APPOINTMENT_LEAD_HOURS)
    last_day = timezone.localdate(now) + timedelta(days=settings.APPOINTMENT_BOOKING_DAYS)
    return earliest, last_day


def _slot_starts(garage: Garage, day: date) -> list[datetime]:
    if day.weekday() not in garage.working_days:
        return []
    tz = timezone.get_current_timezone()
    step = timedelta(minutes=garage.slot_minutes)
    start = timezone.make_aware(datetime.combine(day, garage.opens_at), tz)
    close = timezone.make_aware(datetime.combine(day, garage.closes_at), tz)
    starts = []
    while start + step <= close:
        starts.append(start)
        start += step
    return starts


def available_slots(garage: Garage, day: date, now: datetime | None = None) -> list[tuple[datetime, datetime]]:
    earliest, last_day = booking_window(now)
    if not garage.is_active or day > last_day:
        return []
    starts = [s for s in _slot_starts(garage, day) if s >= earliest]
    if not starts:
        return []

    taken = Counter(
        Appointment.objects.filter(
            garage=garage,
            status__in=Appointment.ACTIVE_STATUSES,
            slot_start__gte=starts[0],
            slot_start__lte=starts[-1],
        ).values_list("slot_start", flat=True)
    )
    step = timedelta(minutes=garage.slot_minutes)
    return [(s, s + step) for s in starts if taken[s] < garage.capacity_per_slot]


def hold_slot(garage: Garage, slot_start: datetime, order) -> Appointment:
    """Reserve a slot for an unpaid order. Must run inside a transaction."""
    Garage.objects.select_for_update().filter(pk=garage.pk).first()  # serialize bookings per garage
    day = timezone.localdate(slot_start)
    free = {start for start, _ in available_slots(garage, day)}
    if slot_start not in free:
        raise ValidationError({"slot_start": ["This time slot is no longer available."]})
    return Appointment.objects.create(
        garage=garage,
        order=order,
        slot_start=slot_start,
        slot_end=slot_start + timedelta(minutes=garage.slot_minutes),
    )


def set_status(appointment: Appointment, status: str) -> None:
    appointment.status = status
    appointment.save(update_fields=["status", "updated_at"])
