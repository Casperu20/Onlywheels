import { ArrowLeft, Minus, Plus, ShoppingCart } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { toast } from "sonner";

import { getErrorMessage } from "@/api/errors";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { useCartActions } from "@/features/cart";
import {
  FitmentBadge,
  WheelVisual,
  defaultQuantity,
  useProduct,
  variantSummary,
  type ProductDetail,
} from "@/features/catalog";
import { FavoriteButton } from "@/features/favorites";
import { ReviewsSection } from "@/features/reviews";
import { useVehicleStore } from "@/features/vehicle";
import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import { NotFoundPage } from "@/routes/ErrorPages";

export function ProductPage() {
  const { slug = "" } = useParams();
  const [searchParams] = useSearchParams();
  const activeVehicle = useVehicleStore((s) => s.active);
  const vehicle = searchParams.get("vehicle") ?? activeVehicle?.id;
  const { data: product, isPending, isError } = useProduct(slug, vehicle);

  if (isPending) return <PageLoader />;
  if (isError || !product) return <NotFoundPage />;
  const label = vehicle && vehicle === activeVehicle?.id ? activeVehicle.label : undefined;
  return <ProductView key={product.id} product={product} vehicleLabel={label} />;
}

function ProductView({ product, vehicleLabel }: { product: ProductDetail; vehicleLabel?: string }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";
  const preferred = product.variants.find((v) => v.fitment?.fits) ?? product.variants[0];
  const [variantId, setVariantId] = useState(preferred?.id);
  const [quantity, setQuantity] = useState(defaultQuantity(product.type));
  const variant = product.variants.find((v) => v.id === variantId) ?? preferred;
  const image = product.media[0];
  const navigate = useNavigate();
  const addToCart = useCartActions().add;

  const onAddToCart = () => {
    if (!variant) return;
    addToCart.mutate(
      {
        variantId: variant.id,
        quantity,
        product: { id: product.id, slug: product.slug, name: product.name, type: product.type, brand: product.brand.name },
        variant,
      },
      {
        onSuccess: () =>
          toast.success(t("cart.added"), { action: { label: t("cart.view"), onClick: () => navigate("/cart") } }),
        onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
      },
    );
  };

  return (
    <section className="container-page py-8">
      <Link to="/catalog" className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" aria-hidden /> {t("product.back")}
      </Link>

      <div className="grid gap-10 lg:grid-cols-2">
        <div className="relative rounded-3xl border border-border bg-linear-to-b from-[#202227] to-card p-10">
          {image ? (
            <img src={image.image} alt={image.alt || product.name} className="mx-auto aspect-square w-4/5 object-contain" />
          ) : (
            <WheelVisual type={product.type} finish={variant?.finish} className="mx-auto w-4/5" />
          )}
          <FavoriteButton productId={product.id} isFavorite={product.is_favorite} className="absolute top-4 right-4" />
        </div>

        <div className="flex flex-col gap-5">
          <div>
            <p className="text-xs font-bold tracking-[2px] text-muted-foreground uppercase">{product.brand.name}</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight md:text-4xl">{product.name}</h1>
            {product.badge && (
              <span className="mt-3 inline-block rounded bg-[#35251e] px-2 py-0.5 text-xs font-bold text-[#ff9a70]">
                {product.badge}
              </span>
            )}
          </div>

          {vehicleLabel && (
            <p className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground">
              {t("product.checkedFor", { vehicle: vehicleLabel })}
            </p>
          )}

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-semibold">{t("product.chooseVariant")}</legend>
            {product.variants.map((v) => (
              <label
                key={v.id}
                className={cn(
                  "flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-3",
                  v.id === variant?.id ? "border-primary bg-primary/5" : "border-border hover:border-[#45484f]",
                )}
              >
                <span className="flex items-center gap-3">
                  <input
                    type="radio"
                    name="variant"
                    value={v.id}
                    checked={v.id === variant?.id}
                    onChange={() => setVariantId(v.id)}
                    className="accent-primary"
                  />
                  <span className="flex flex-col">
                    <span className="text-sm">
                      {variantSummary(v, product.type)}
                      {v.finish && ` · ${t(`catalog.finishes.${v.finish}`)}`}
                    </span>
                    {v.fitment && <FitmentBadge fitment={v.fitment} />}
                  </span>
                </span>
                <span className="text-right">
                  <span className="block font-bold">{formatPrice(v.price, locale)}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {v.available > 0 ? t("product.available", { count: v.available }) : t("catalog.onOrder")}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>

          {variant && (
            <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">{t("product.quantity")}</span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="icon"
                    aria-label={t("product.decrease")}
                    disabled={quantity <= 1}
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                  >
                    <Minus aria-hidden />
                  </Button>
                  <span className="w-8 text-center font-bold" aria-live="polite">
                    {quantity}
                  </span>
                  <Button
                    variant="secondary"
                    size="icon"
                    aria-label={t("product.increase")}
                    onClick={() => setQuantity((q) => Math.min(20, q + 1))}
                  >
                    <Plus aria-hidden />
                  </Button>
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-muted-foreground">{t("product.total")}</span>
                <span className="text-2xl font-extrabold">
                  {formatPrice(Number(variant.price) * quantity, locale)}
                </span>
              </div>
              <Button disabled={addToCart.isPending} onClick={onAddToCart}>
                <ShoppingCart aria-hidden /> {t("product.addToCart")}
              </Button>
            </div>
          )}

          {product.description && <p className="leading-relaxed text-muted-foreground">{product.description}</p>}
          <p className="text-xs text-muted-foreground">{t("catalog.demoNote")}</p>
        </div>
      </div>

      <ReviewsSection
        productId={product.id}
        productSlug={product.slug}
        ratingAvg={product.rating_avg}
        ratingCount={product.rating_count}
      />
    </section>
  );
}
