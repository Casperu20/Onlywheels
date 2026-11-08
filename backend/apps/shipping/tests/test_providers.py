from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

from apps.shipping.providers import (
    CarrierAmbiguousError,
    CarrierConfigurationError,
    CarrierRejectedError,
    FanCourierProvider,
    SamedayProvider,
    classify_carrier_status,
    get_carrier_provider,
)
from tests.factories import make_order

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 label"


def _response(*, body=None, status_code=200, content=b""):
    response = Mock()
    response.status_code = status_code
    response.content = content
    if body is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = body
    return response


@pytest.fixture
def sameday_settings(settings):
    settings.SHIPPING_CARRIER = "sameday"
    settings.SHIPPING_MODE = "sandbox"
    settings.SAMEDAY_API_BASE_URL = ""
    settings.SAMEDAY_USERNAME = "demo-user"
    settings.SAMEDAY_PASSWORD = "demo-pass"
    settings.SAMEDAY_PICKUP_POINT_ID = "11"
    settings.SAMEDAY_SERVICE_ID = "7"
    settings.SAMEDAY_TRACKING_URL = "https://track.example/sameday/{awb}"
    return settings


@pytest.fixture
def fan_settings(settings):
    settings.SHIPPING_CARRIER = "fan_courier"
    settings.SHIPPING_MODE = "sandbox"
    settings.FAN_COURIER_API_BASE_URL = "https://api.fancourier.ro"
    settings.FAN_COURIER_CLIENT_ID = "7032158"
    settings.FAN_COURIER_USERNAME = "fan-user"
    settings.FAN_COURIER_PASSWORD = "fan-pass"
    settings.FAN_COURIER_SERVICE = "Standard"
    settings.FAN_COURIER_TRACKING_URL = "https://track.example/fan/{awb}"
    return settings


PARCELS = [Decimal("11.00"), Decimal("11.00"), Decimal("1.50")]


# --- Factory / configuration -------------------------------------------------------------


def test_disabled_carrier_is_a_configuration_error(settings):
    settings.SHIPPING_CARRIER = ""
    with pytest.raises(CarrierConfigurationError, match="disabled"):
        get_carrier_provider()


def test_unknown_carrier_is_a_configuration_error(settings):
    settings.SHIPPING_CARRIER = "dhl"
    with pytest.raises(CarrierConfigurationError):
        get_carrier_provider()


def test_factory_returns_the_configured_carrier(sameday_settings):
    assert isinstance(get_carrier_provider(), SamedayProvider)
    sameday_settings.SHIPPING_CARRIER = "fan_courier"
    assert isinstance(get_carrier_provider(), FanCourierProvider)


def test_missing_credentials_fail_before_any_request(sameday_settings, user):
    sameday_settings.SAMEDAY_PASSWORD = ""
    with patch("requests.post") as post, pytest.raises(CarrierConfigurationError):
        SamedayProvider().create_awb(make_order(user), parcels=PARCELS)
    post.assert_not_called()


def test_sameday_mode_selects_demo_or_live_host(sameday_settings):
    assert SamedayProvider().base_url == "https://sameday-api.demo.zitec.com"
    sameday_settings.SHIPPING_MODE = "live"
    assert SamedayProvider().base_url == "https://api.sameday.ro"
    sameday_settings.SHIPPING_MODE = "prod"
    with pytest.raises(CarrierConfigurationError, match="SHIPPING_MODE"):
        SamedayProvider().base_url  # noqa: B018


# --- Status mapping ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Livrat cu succes", "delivered"),
        ("Delivered", "delivered"),
        ("Nelivrat - destinatar absent", None),
        ("Colet returnat la expeditor", "returned"),
        ("Ridicat de la expeditor", "picked_up"),
        ("In tranzit spre hub", "in_transit"),
        ("In curs de livrare", "in_transit"),
        ("Something new", None),
        ("", None),
    ],
)
def test_classify_carrier_status(text, expected):
    assert classify_carrier_status(text) == expected


# --- Sameday -----------------------------------------------------------------------------


def _sameday_auth():
    return _response(body={"token": "tok-1", "expires_at": "2099-01-01 00:00"})


def test_sameday_creates_awb_with_form_payload(sameday_settings, user):
    order = make_order(user)
    with patch(
        "requests.post", side_effect=[_sameday_auth(), _response(body={"awbNumber": "1ONB123", "parcels": []})]
    ) as post:
        result = SamedayProvider().create_awb(order, parcels=PARCELS)

    assert result.awb == "1ONB123"
    assert result.tracking_url == "https://track.example/sameday/1ONB123"
    auth_call, awb_call = post.call_args_list
    assert auth_call.args == ("https://sameday-api.demo.zitec.com/api/authenticate",)
    assert auth_call.kwargs["headers"] == {"X-AUTH-USERNAME": "demo-user", "X-AUTH-PASSWORD": "demo-pass"}
    assert awb_call.args == ("https://sameday-api.demo.zitec.com/api/awb",)
    assert awb_call.kwargs["headers"] == {"X-AUTH-TOKEN": "tok-1"}
    assert awb_call.kwargs["timeout"] > 0
    data = awb_call.kwargs["data"]
    assert data["pickupPoint"] == "11"
    assert data["service"] == "7"
    assert data["packageNumber"] == 3
    assert data["packageWeight"] == "23.50"
    assert data["parcels[2][weight]"] == "1.50"
    assert data["cashOnDelivery"] == 0
    assert data["clientInternalReference"] == order.number
    assert data["awbRecipient[name]"] == order.full_name
    assert data["awbRecipient[cityString]"] == order.city
    assert data["awbRecipient[countyString]"] == order.county
    assert data["awbRecipient[phoneNumber]"] == order.phone


def test_sameday_bad_credentials_are_a_configuration_error(sameday_settings, user):
    with patch("requests.post", return_value=_response(body={"error": "bad"}, status_code=401)) as post:
        with pytest.raises(CarrierConfigurationError):
            SamedayProvider().create_awb(make_order(user), parcels=PARCELS)
    assert post.call_count == 1


def test_sameday_validation_error_is_a_rejection(sameday_settings, user):
    rejected = _response(
        body={"errors": {"children": {"awbRecipient": {"errors": ["City not found"]}}}}, status_code=400
    )
    with patch("requests.post", side_effect=[_sameday_auth(), rejected]):
        with pytest.raises(CarrierRejectedError, match="City not found"):
            SamedayProvider().create_awb(make_order(user), parcels=PARCELS)


@pytest.mark.parametrize(
    "awb_response",
    [
        requests.Timeout("slow"),
        _response(body={"error": "boom"}, status_code=502),
        _response(body={"parcels": []}),
        _response(body=None),
    ],
)
def test_sameday_unknown_outcome_is_ambiguous(sameday_settings, user, awb_response):
    with patch("requests.post", side_effect=[_sameday_auth(), awb_response]):
        with pytest.raises(CarrierAmbiguousError):
            SamedayProvider().create_awb(make_order(user), parcels=PARCELS)


def test_sameday_login_network_error_is_not_ambiguous(sameday_settings, user):
    with patch("requests.post", side_effect=requests.ConnectionError("down")):
        with pytest.raises(CarrierRejectedError, match="unreachable"):
            SamedayProvider().create_awb(make_order(user), parcels=PARCELS)


def test_sameday_downloads_a4_label(sameday_settings):
    with (
        patch("requests.post", return_value=_sameday_auth()),
        patch("requests.get", return_value=_response(content=PDF)) as get,
    ):
        assert SamedayProvider().download_label("1ONB123") == PDF
    assert get.call_args.args == ("https://sameday-api.demo.zitec.com/api/awb/download/1ONB123/A4",)


def test_sameday_label_must_be_a_pdf(sameday_settings):
    with (
        patch("requests.post", return_value=_sameday_auth()),
        patch("requests.get", return_value=_response(content=b"<html>")),
        pytest.raises(CarrierRejectedError),
    ):
        SamedayProvider().download_label("1ONB123")


def test_sameday_track_maps_latest_history_entry(sameday_settings):
    body = {
        "expeditionHistory": [
            {
                "statusId": 9,
                "status": "Livrat",
                "statusLabel": "Livrat",
                "statusState": "Livrat",
                "statusDate": "2026-11-10T10:00:00+0200",
            },
            {
                "statusId": 4,
                "status": "In tranzit",
                "statusLabel": "In tranzit",
                "statusState": "In tranzit",
                "statusDate": "2026-11-09T10:00:00+0200",
            },
        ]
    }
    with (
        patch("requests.post", return_value=_sameday_auth()),
        patch("requests.get", return_value=_response(body=body)) as get,
    ):
        update = SamedayProvider().track("1ONB123")
    assert get.call_args.args == ("https://sameday-api.demo.zitec.com/api/client/awb/1ONB123/status",)
    assert update.status == "delivered"
    assert update.label == "Livrat"


# --- Fan Courier -------------------------------------------------------------------------


def _fan_auth():
    return _response(body={"status": "success", "data": {"token": "fan-tok", "expiresAt": "2099-01-01 00:00:00"}})


def test_fan_courier_creates_awb_with_json_payload(fan_settings, user):
    order = make_order(user)
    created = _response(body={"response": [{"awbNumber": 2400000123, "errors": None}]})
    with patch("requests.post", side_effect=[_fan_auth(), created]) as post:
        result = FanCourierProvider().create_awb(order, parcels=PARCELS)

    assert result.awb == "2400000123"
    assert result.tracking_url == "https://track.example/fan/2400000123"
    auth_call, awb_call = post.call_args_list
    assert auth_call.args == ("https://api.fancourier.ro/login",)
    assert auth_call.kwargs["json"] == {"username": "fan-user", "password": "fan-pass"}
    assert awb_call.args == ("https://api.fancourier.ro/intern-awb",)
    assert awb_call.kwargs["headers"] == {"Authorization": "Bearer fan-tok"}
    body = awb_call.kwargs["json"]
    assert body["clientId"] == "7032158"
    shipment = body["shipments"][0]
    assert shipment["info"]["packages"] == {"parcel": 3, "envelope": 0}
    assert shipment["info"]["weight"] == 24
    assert shipment["info"]["payment"] == "expeditor"
    assert shipment["info"]["cod"] == 0
    assert shipment["info"]["observation"] == order.number
    assert shipment["recipient"]["name"] == order.full_name
    assert shipment["recipient"]["address"]["locality"] == order.city


def test_fan_courier_per_shipment_errors_are_a_rejection(fan_settings, user):
    rejected = _response(body={"response": [{"awbNumber": None, "errors": {"recipient.phone": "Invalid phone"}}]})
    with patch("requests.post", side_effect=[_fan_auth(), rejected]):
        with pytest.raises(CarrierRejectedError, match="Invalid phone"):
            FanCourierProvider().create_awb(make_order(user), parcels=PARCELS)


def test_fan_courier_server_error_is_ambiguous(fan_settings, user):
    with patch("requests.post", side_effect=[_fan_auth(), _response(body={}, status_code=500)]):
        with pytest.raises(CarrierAmbiguousError):
            FanCourierProvider().create_awb(make_order(user), parcels=PARCELS)


def test_fan_courier_downloads_label(fan_settings):
    with (
        patch("requests.post", return_value=_fan_auth()),
        patch("requests.get", return_value=_response(content=PDF)) as get,
    ):
        assert FanCourierProvider().download_label("2400000123") == PDF
    assert get.call_args.args == ("https://api.fancourier.ro/awb/label",)
    assert get.call_args.kwargs["params"]["awbs[]"] == "2400000123"


def test_fan_courier_track_maps_last_event(fan_settings):
    body = {
        "status": "success",
        "data": [
            {
                "awbNumber": "2400000123",
                "events": [{"id": "C0", "name": "Ridicat de la expeditor"}, {"id": "H4", "name": "In tranzit"}],
            }
        ],
    }
    with (
        patch("requests.post", return_value=_fan_auth()),
        patch("requests.get", return_value=_response(body=body)),
    ):
        update = FanCourierProvider().track("2400000123")
    assert update.status == "in_transit"
    assert update.label == "In tranzit"


def test_tracking_failure_raises_a_carrier_error(fan_settings):
    with (
        patch("requests.post", return_value=_fan_auth()),
        patch("requests.get", side_effect=requests.Timeout("slow")),
        pytest.raises(CarrierRejectedError),
    ):
        FanCourierProvider().track("2400000123")
