from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.appointments.services import available_slots
from tests.factories import make_garage, make_order

pytestmark = pytest.mark.django_db


def local(day, hour) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


@pytest.fixture
def day():
    return timezone.localdate() + timedelta(days=3)


def test_slots_follow_opening_hours(day):
    garage = make_garage(opens_at=time(8, 0), closes_at=time(18, 0), slot_minutes=60)
    slots = available_slots(garage, day)
    assert len(slots) == 10
    assert slots[0] == (local(day, 8), local(day, 9))
    assert slots[-1][0] == local(day, 17)


def test_closed_day_has_no_slots(day):
    garage = make_garage(working_days=[d for d in range(7) if d != day.weekday()])
    assert available_slots(garage, day) == []


def test_lead_time_hides_early_slots(day):
    garage = make_garage()
    now = local(day, 10) - timedelta(hours=24)
    starts = [s for s, _ in available_slots(garage, day, now=now)]
    assert starts[0] == local(day, 10)


def test_booking_window(day):
    garage = make_garage()
    assert available_slots(garage, timezone.localdate() + timedelta(days=30)) == []


def test_capacity_and_cancelled_appointments(day, user):
    garage = make_garage(capacity_per_slot=1)
    start = local(day, 9)
    Appointment.objects.create(
        garage=garage, order=make_order(user), slot_start=start, slot_end=start + timedelta(hours=1)
    )
    assert start not in [s for s, _ in available_slots(garage, day)]

    Appointment.objects.update(status=Appointment.Status.CANCELLED)
    assert start in [s for s, _ in available_slots(garage, day)]


def test_slots_api(api_client, day):
    garage = make_garage()
    response = api_client.get(f"/api/v1/garages/{garage.slug}/slots/", {"date": day.isoformat()})
    assert response.status_code == 200
    assert len(response.json()) == 10

    assert api_client.get(f"/api/v1/garages/{garage.slug}/slots/").status_code == 400


def test_garage_list_is_public(api_client):
    garage = make_garage()
    make_garage(is_active=False)
    assert [g["slug"] for g in api_client.get("/api/v1/garages/").json()] == [garage.slug]
