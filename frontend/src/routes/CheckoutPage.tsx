import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { CreditCard, Tag } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { applyFieldErrors, getApiError, getErrorMessage } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/features/auth";
import { cartKey, useCart } from "@/features/cart";
import { variantSummary } from "@/features/catalog";
import { checkoutApi, checkoutSchema, useAddresses, useQuote, type CheckoutValues } from "@/features/checkout";
import { GaragePicker, isoDate, type GarageSelection } from "@/features/garages";
import { TotalsTable, ordersApi } from "@/features/orders";
import { formatPrice } from "@/lib/format";
import { useLocale } from "@/lib/useLocale";
import { cn } from "@/lib/utils";

function Step({ number, title, children }: { number: number; title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-6" aria-labelledby={`step-${number}`}>
      <h2 id={`step-${number}`} className="mb-5 flex items-center gap-3 font-semibold">
        <span className="grid size-7 place-items-center rounded-full bg-primary text-xs font-extrabold text-primary-foreground">
          {number}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function CheckoutPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const queryClient = useQueryClient();
  const { data: user } = useMe();
  const cart = useCart();
  const addresses = useAddresses();

  const [garage, setGarage] = useState<GarageSelection>({ date: isoDate(2) });
  const [garageError, setGarageError] = useState<string>();
  const [voucherInput, setVoucherInput] = useState("");
  const [voucher, setVoucher] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    resolver: zodResolver(checkoutSchema),
    defaultValues: {
      delivery_method: "courier",
      email: user?.email ?? "",
      full_name: user ? `${user.first_name} ${user.last_name}`.trim() : "",
      phone: user?.phone ?? "",
      line1: "",
      line2: "",
      city: "",
      county: "",
      postal_code: "",
      notes: "",
      save_address: true,
      accept_terms: false,
    } satisfies CheckoutValues,
  });
  const { register, handleSubmit, watch, setValue, setError, reset, getValues, formState } = form;
  const { errors } = formState;
  const delivery = watch("delivery_method");

  // Prefill from the default saved address once it is loaded.
  const savedAddress = addresses.data?.find((a) => a.is_default) ?? addresses.data?.[0];
  useEffect(() => {
    if (!savedAddress || formState.isDirty) return;
    reset({
      ...getValues(),
      full_name: savedAddress.full_name,
      phone: savedAddress.phone,
      line1: savedAddress.line1,
      line2: savedAddress.line2,
      city: savedAddress.city,
      county: savedAddress.county,
      postal_code: savedAddress.postal_code,
      save_address: false,
    });
  }, [savedAddress, formState.isDirty, reset, getValues]);

  const quoteRequest = {
    delivery_method: delivery,
    garage_id: delivery === "garage_fitting" ? garage.garageId : undefined,
    voucher_code: voucher || undefined,
  };
  const quote = useQuote(quoteRequest, cart.lines.length > 0 && (delivery === "courier" || Boolean(garage.garageId)));
  const voucherError = getApiError(quote.error)?.fields?.voucher_code?.[0];

  if (cart.isLoading) return <PageLoader />;
  if (cart.lines.length === 0) {
    return (
      <section className="container-page py-16 text-center">
        <p className="font-semibold">{t("cart.empty")}</p>
        <Button asChild className="mt-6">
          <Link to="/catalog">{t("home.ctaCatalog")}</Link>
        </Button>
      </section>
    );
  }

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    setGarageError(undefined);
    if (values.delivery_method === "garage_fitting" && (!garage.garageId || !garage.slotStart)) {
      setGarageError(t("checkout.chooseSlot"));
      return;
    }
    setSubmitting(true);
    try {
      const order = await checkoutApi.createOrder({
        ...values,
        garage_id: values.delivery_method === "garage_fitting" ? garage.garageId : undefined,
        slot_start: values.delivery_method === "garage_fitting" ? garage.slotStart : undefined,
        voucher_code: voucher || undefined,
      });
      await queryClient.invalidateQueries({ queryKey: cartKey });
      if (values.save_address) {
        await checkoutApi
          .saveAddress({
            full_name: values.full_name,
            phone: values.phone,
            line1: values.line1,
            line2: values.line2 ?? "",
            city: values.city,
            county: values.county,
            postal_code: values.postal_code,
            is_default: !addresses.data?.length,
          })
          .catch(() => undefined);
      }
      const { checkout_url } = await ordersApi.pay(order.number);
      window.location.assign(checkout_url);
    } catch (error) {
      const fields = getApiError(error)?.fields;
      if (fields?.slot_start || fields?.garage_id) {
        setGarageError((fields.slot_start ?? fields.garage_id)[0]);
      }
      if (!applyFieldErrors(error, setError)) {
        setFormError(getErrorMessage(error, t("auth.genericError")));
      }
      setSubmitting(false);
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="container-page grid gap-8 py-10 lg:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-6">
        <h1 className="text-3xl font-extrabold tracking-tight">{t("checkout.title")}</h1>
        {formError && (
          <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {formError}
          </p>
        )}

        <Step number={1} title={t("checkout.contact")}>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label={t("auth.email")} type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
            <FormField label={t("checkout.phone")} type="tel" autoComplete="tel" error={errors.phone?.message} {...register("phone")} />
            <FormField
              label={t("checkout.fullName")}
              autoComplete="name"
              containerClassName="md:col-span-2"
              error={errors.full_name?.message}
              {...register("full_name")}
            />
          </div>
        </Step>

        <Step number={2} title={t("checkout.delivery")}>
          <div role="radiogroup" className="grid gap-3 md:grid-cols-2">
            {(["courier", "garage_fitting"] as const).map((method) => (
              <button
                key={method}
                type="button"
                role="radio"
                aria-checked={delivery === method}
                onClick={() => setValue("delivery_method", method)}
                className={cn(
                  "rounded-xl border p-4 text-left",
                  delivery === method ? "border-primary bg-primary/5" : "border-border hover:border-[#45484f]",
                )}
              >
                <p className="font-semibold">{t(`checkout.methods.${method}.title`)}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t(`checkout.methods.${method}.text`)}</p>
              </button>
            ))}
          </div>
          {delivery === "garage_fitting" && (
            <div className="mt-6">
              <GaragePicker value={garage} onChange={setGarage} error={garageError} />
            </div>
          )}
        </Step>

        <Step number={3} title={delivery === "courier" ? t("checkout.address") : t("checkout.billingAddress")}>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label={t("checkout.line1")}
              autoComplete="address-line1"
              containerClassName="md:col-span-2"
              error={errors.line1?.message}
              {...register("line1")}
            />
            <FormField label={t("checkout.line2")} autoComplete="address-line2" error={errors.line2?.message} {...register("line2")} />
            <FormField label={t("checkout.city")} autoComplete="address-level2" error={errors.city?.message} {...register("city")} />
            <FormField label={t("checkout.county")} autoComplete="address-level1" error={errors.county?.message} {...register("county")} />
            <FormField
              label={t("checkout.postalCode")}
              inputMode="numeric"
              autoComplete="postal-code"
              error={errors.postal_code?.message}
              {...register("postal_code")}
            />
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            <Label htmlFor="checkout-notes">{t("checkout.notes")}</Label>
            <textarea
              id="checkout-notes"
              rows={2}
              className="rounded-md border border-input bg-[#15171b] px-3 py-2 text-sm"
              {...register("notes")}
            />
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4 accent-primary" {...register("save_address")} />
            {t("checkout.saveAddress")}
          </label>
        </Step>
      </div>

      <aside className="flex h-fit flex-col gap-5 rounded-2xl border border-border bg-card p-6 lg:sticky lg:top-28">
        <h2 className="font-semibold">{t("checkout.summary")}</h2>
        <ul className="flex flex-col gap-3 text-sm">
          {cart.lines.map((line) => (
            <li key={line.key} className="flex justify-between gap-3">
              <span>
                {line.quantity} × {line.product.brand} {line.product.name}
                <span className="block text-xs text-muted-foreground">{variantSummary(line.variant, line.product.type)}</span>
              </span>
              <span className="shrink-0">{formatPrice(line.lineTotal, locale)}</span>
            </li>
          ))}
        </ul>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="voucher">{t("checkout.voucher")}</Label>
          <div className="flex gap-2">
            <Input
              id="voucher"
              value={voucherInput}
              onChange={(e) => setVoucherInput(e.target.value.toUpperCase())}
              aria-invalid={voucherError ? true : undefined}
            />
            <Button type="button" variant="secondary" onClick={() => setVoucher(voucherInput.trim())}>
              <Tag aria-hidden /> {t("checkout.apply")}
            </Button>
          </div>
          {voucherError && <p className="text-xs text-destructive">{voucherError}</p>}
        </div>

        {quote.data ? (
          <TotalsTable totals={quote.data} />
        ) : (
          <p className="text-sm text-muted-foreground">
            {delivery === "garage_fitting" && !garage.garageId ? t("checkout.chooseGarage") : t("common.loading")}
          </p>
        )}

        <label className="flex items-start gap-2 text-xs">
          <input type="checkbox" className="mt-0.5 size-4 accent-primary" {...register("accept_terms")} />
          <span>
            {t("checkout.acceptTerms")}
            {errors.accept_terms?.message && (
              <span className="block text-destructive">{t(errors.accept_terms.message)}</span>
            )}
          </span>
        </label>

        <Button type="submit" size="lg" disabled={submitting || !quote.data}>
          <CreditCard aria-hidden /> {submitting ? t("common.loading") : t("checkout.pay")}
        </Button>
        <p className="text-xs text-muted-foreground">{t("checkout.payHint")}</p>
      </aside>
    </form>
  );
}
