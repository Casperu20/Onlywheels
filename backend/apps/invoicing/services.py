"""
Invoicing + e-Factura (phase 2) through SmartBill (or Oblio).

Planned flow:
1. `orders.services.mark_paid` schedules `issue_invoice_task(order_id)` on commit.
2. The task calls SmartBill `POST /SBORO/api/invoice` with company CIF, series, client data
   (from the order snapshot; company clients add CUI/Reg. Com. fields at checkout),
   one line per OrderItem + shipping/fitting lines, VAT rate from settings.VAT_RATE,
   and `useStock=false`. The discount is sent as a negative line.
3. SmartBill returns series + number; the PDF is downloaded from `GET /SBORO/api/invoice/pdf`
   and stored in `Invoice.pdf`. SmartBill also submits the e-Factura XML to ANAF (SPV);
   a daily task refreshes `efactura_status`.
4. The invoice PDF link is added to the order page and the "order paid" email.
5. Cancelling a paid order issues a storno (reverse) invoice via `POST /SBORO/api/invoice/reverse`.

Credentials: SMARTBILL_USER, SMARTBILL_TOKEN, SMARTBILL_CIF, SMARTBILL_SERIES (env only).
"""

from apps.orders.models import Order

from .models import Invoice


def issue_invoice(order: Order) -> Invoice:
    raise NotImplementedError("SmartBill invoicing is planned for phase 2 (see module docstring).")
