import { useTranslation } from "react-i18next";

import { formatPrice } from "@/lib/format";
import { useLocale } from "@/lib/useLocale";
import { cn } from "@/lib/utils";

import type { OrderDetail, OrderStatus } from "../api";

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending_payment: "bg-[#35251e] text-[#ff9a70]",
  paid: "bg-success/15 text-success",
  processing: "bg-success/15 text-success",
  shipped: "bg-success/15 text-success",
  ready_for_fitting: "bg-success/15 text-success",
  completed: "bg-secondary text-foreground",
  cancelled: "bg-destructive/15 text-destructive",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useTranslation();
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", STATUS_STYLES[status])}>
      {t(`orders.status.${status}`)}
    </span>
  );
}

/** Totals block shared by the checkout summary and the order page. */
export function TotalsTable({
  totals,
}: {
  totals: Pick<OrderDetail, "subtotal" | "discount" | "shipping" | "fitting" | "total" | "vat"> & {
    voucher_code?: string | null;
  };
}) {
  const { t } = useTranslation();
  const locale = useLocale();
  const row = (label: string, value: string, negative = false) => (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>
        {negative ? "−" : ""}
        {formatPrice(value, locale)}
      </dd>
    </div>
  );

  return (
    <dl className="flex flex-col gap-2 text-sm">
      {row(t("checkout.subtotal"), totals.subtotal)}
      {Number(totals.discount) > 0 &&
        row(`${t("checkout.discount")}${totals.voucher_code ? ` (${totals.voucher_code})` : ""}`, totals.discount, true)}
      {row(t("checkout.shipping"), totals.shipping)}
      {Number(totals.fitting) > 0 && row(t("checkout.fitting"), totals.fitting)}
      <div className="mt-2 flex justify-between gap-4 border-t border-border pt-3 text-base font-extrabold">
        <dt>{t("checkout.total")}</dt>
        <dd>{formatPrice(totals.total, locale)}</dd>
      </div>
      <p className="text-right text-xs text-muted-foreground">
        {t("checkout.vatIncluded", { vat: formatPrice(totals.vat, locale) })}
      </p>
    </dl>
  );
}
