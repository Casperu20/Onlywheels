"""
Courier integration (phase 2): Sameday and Fan Courier AWBs.

Planned flow:
1. Staff marks an order "processing" → Celery task `create_shipment(order_id)`:
   picks the carrier (setting or per-order choice), computes parcels/weight from the
   order items (wheels ≈ 10–12 kg each, tires ≈ 9–11 kg), calls `provider.create_awb()`,
   stores AWB number + PDF label in `Shipment`, and moves the order to "shipped".
   For garage fitting the delivery address is the partner garage.
2. Celery Beat polls `provider.track(awb)` every hour for undelivered shipments and updates
   `Shipment.status`; "delivered" completes courier orders (garage orders wait for fitting).
3. The customer sees `tracking_url` on the order page and gets the status email.

Each carrier is an adapter in `providers/` behind `CarrierProvider` so they can be swapped.
"""

from apps.orders.models import Order

from .models import Shipment


def create_shipment(order: Order) -> Shipment:
    raise NotImplementedError("Courier integration is planned for phase 2 (see module docstring).")
