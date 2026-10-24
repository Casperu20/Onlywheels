import { CheckCircle2, CircleX, Clock, CreditCard, MapPin } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { toast } from "sonner";

import { getErrorMessage } from "@/api/errors";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { GarageCard, useGarages } from "@/features/garages";
import {
  OrderStatusBadge,
  TotalsTable,
  ordersApi,
  useCancelOrder,
  useOrder,
  useOrders,
  usePayOrder,
} from "@/features/orders";
import { formatPrice } from "@/lib/format";
import { useLocale } from "@/lib/useLocale";
import { NotFoundPage } from "@/routes/ErrorPages";

function formatDateTime(value: string, locale: string) {
  return new Date(value).toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" });
}

export function OrdersPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const { data, isPending } = useOrders();

  return (
    <section className="container-page flex flex-col gap-6 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight">{t("orders.title")}</h1>
      </div>
      {isPending ? (
        <PageLoader />
      ) : data?.results.length ? (
        <ul className="flex flex-col gap-3">
          {data.results.map((order) => (
            <li key={order.number}>
              <Link
                to={`/account/orders/${order.number}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border p-5 hover:border-[#45484f]"
              >
                <div>
                  <p className="font-semibold">{order.number}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDateTime(order.created_at, locale)} · {t("orders.pieces", { count: order.item_count })}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <OrderStatusBadge status={order.status} />
                  <span className="font-bold">{formatPrice(order.total, locale)}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted-foreground">{t("orders.empty")}</p>
      )}
    </section>
  );
}

export function OrderDetailPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const { number = "" } = useParams();
  const [params] = useSearchParams();
  const { data: order, isPending, isError } = useOrder(number);
  const pay = usePayOrder();
  const cancel = useCancelOrder();

  if (isPending) return <PageLoader />;
  if (isError || !order) return <NotFoundPage />;

  return (
    <section className="container-page grid gap-8 py-10 lg:grid-cols-[1fr_360px]">
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-extrabold tracking-tight">{order.number}</h1>
          <OrderStatusBadge status={order.status} />
        </div>
        {params.get("payment") === "cancelled" && order.status === "pending_payment" && (
          <p role="status" className="rounded-md bg-[#35251e] px-3 py-2 text-sm text-[#ff9a70]">
            {t("orders.paymentCancelled")}
          </p>
        )}

        <ul className="flex flex-col gap-3">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-4 rounded-xl border border-border p-4 text-sm">
              <span>
                <span className="font-semibold">
                  {item.quantity} × {item.product_name}
                </span>
                <span className="block text-xs text-muted-foreground">{item.description}</span>
              </span>
              <span className="shrink-0 font-bold">{formatPrice(item.line_total, locale)}</span>
            </li>
          ))}
        </ul>

        {order.appointment ? (
          <div className="rounded-2xl border border-border p-5 text-sm">
            <p className="flex items-center gap-2 font-semibold">
              <MapPin className="size-4 text-primary" aria-hidden /> {t("orders.fittingAt", { garage: order.appointment.garage.name })}
            </p>
            <p className="mt-1 text-muted-foreground">
              {order.appointment.garage.address}, {order.appointment.garage.city} · {order.appointment.garage.phone}
            </p>
            <p className="mt-2">
              {formatDateTime(order.appointment.slot_start, locale)} ·{" "}
              {t(`orders.appointment.${order.appointment.status}`)}
            </p>
          </div>
        ) : (
          <div className="rounded-2xl border border-border p-5 text-sm">
            <p className="font-semibold">{t("orders.deliveryTo")}</p>
            <p className="mt-1 text-muted-foreground">
              {order.full_name}, {order.line1}
              {order.line2 && `, ${order.line2}`}, {order.city}, {order.county} {order.postal_code}
            </p>
          </div>
        )}

        <div>
          <h2 className="mb-3 font-semibold">{t("orders.history")}</h2>
          <ol className="flex flex-col gap-3 border-l border-border pl-5">
            {order.status_changes.map((change, index) => (
              <li key={index} className="relative text-sm">
                <span className="absolute top-1.5 -left-[25px] size-2.5 rounded-full bg-primary" aria-hidden />
                <span className="font-semibold">{t(`orders.status.${change.status}`)}</span>
                <span className="ml-2 text-xs text-muted-foreground">{formatDateTime(change.created_at, locale)}</span>
                {change.note && <p className="text-xs text-muted-foreground">{change.note}</p>}
              </li>
            ))}
          </ol>
        </div>
      </div>

      <aside className="flex h-fit flex-col gap-4 rounded-2xl border border-border bg-card p-6">
        <TotalsTable totals={order} />
        {order.can_pay && (
          <>
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="size-3.5" aria-hidden />
              {t("orders.reservedUntil", { time: formatDateTime(order.reserved_until!, locale) })}
            </p>
            <Button
              disabled={pay.isPending}
              onClick={() =>
                pay.mutate(order.number, {
                  onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
                })
              }
            >
              <CreditCard aria-hidden /> {t("checkout.pay")}
            </Button>
          </>
        )}
        {order.can_cancel && (
          <Button
            variant="ghost"
            disabled={cancel.isPending}
            onClick={() =>
              cancel.mutate(order.number, {
                onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
              })
            }
          >
            {t("orders.cancel")}
          </Button>
        )}
      </aside>
    </section>
  );
}

/** Return page after payment. The webhook may arrive a few seconds later, so we poll. */
export function CheckoutSuccessPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const number = params.get("order") ?? "";
  const { data: order, isPending } = useOrder(number, { pollWhilePending: true });

  if (isPending) return <PageLoader />;
  if (!order) return <NotFoundPage />;

  const paid = order.status !== "pending_payment" && order.status !== "cancelled";
  return (
    <section className="container-page grid place-items-center py-20 text-center">
      {paid ? (
        <CheckCircle2 className="size-14 text-success" aria-hidden />
      ) : (
        <Clock className="size-14 animate-pulse text-primary" aria-hidden />
      )}
      <h1 className="mt-6 text-3xl font-extrabold tracking-tight">
        {paid ? t("checkout.successTitle") : t("checkout.waitingTitle")}
      </h1>
      <p className="mt-3 max-w-md text-muted-foreground">
        {paid ? t("checkout.successText", { number: order.number }) : t("checkout.waitingText")}
      </p>
      <Button asChild className="mt-8">
        <Link to={`/account/orders/${order.number}`}>{t("orders.viewOrder")}</Link>
      </Button>
    </section>
  );
}

/** Development stand-in for the payment provider page (PAYMENT_PROVIDER=fake). */
export function FakePayPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const number = params.get("order") ?? "";
  const { data: order, isPending } = useOrder(number);

  if (isPending) return <PageLoader />;
  if (!order) return <NotFoundPage />;

  const complete = async () => {
    try {
      await ordersApi.fakeComplete(order.number);
      navigate(`/checkout/success?order=${order.number}`, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error, t("auth.genericError")));
    }
  };

  return (
    <section className="container-page grid place-items-center py-16">
      <div className="w-full max-w-md rounded-2xl border border-dashed border-primary/60 bg-card p-8 text-center">
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("fakePay.badge")}</p>
        <h1 className="mt-3 text-2xl font-extrabold">{t("fakePay.title")}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t("fakePay.text")}</p>
        <p className="mt-6 text-3xl font-extrabold">{formatPrice(order.total, locale)}</p>
        <p className="text-xs text-muted-foreground">{order.number}</p>
        <div className="mt-8 flex flex-col gap-3">
          <Button onClick={complete}>
            <CheckCircle2 aria-hidden /> {t("fakePay.success")}
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/account/orders/${order.number}?payment=cancelled`)}>
            <CircleX aria-hidden /> {t("fakePay.cancel")}
          </Button>
        </div>
      </div>
    </section>
  );
}

export function FittingPage() {
  const { t } = useTranslation();
  const { data: garages, isPending } = useGarages();

  return (
    <section className="container-page flex flex-col gap-6 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("pages.fitting.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">{t("pages.fitting.title")}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">{t("garages.intro")}</p>
      </div>
      {isPending ? (
        <PageLoader />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {garages?.map((garage) => <GarageCard key={garage.id} garage={garage} />)}
        </div>
      )}
      <Button asChild variant="secondary" className="w-fit">
        <Link to="/catalog">{t("home.ctaCatalog")}</Link>
      </Button>
    </section>
  );
}
