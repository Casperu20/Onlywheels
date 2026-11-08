import { ArrowLeft, Minus, Plus, ShoppingCart, Sparkles } from "lucide-react";
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
  ProductBadge,
  ProductPhoto,
  WheelVisual,
  defaultQuantity,
  useProduct,
  variantSummary,
  type ProductDetail,
} from "@/features/catalog";
import { FavoriteButton } from "@/features/favorites";
import { ReviewsSection } from "@/features/reviews";
import { useVehicleStore } from "@/features/vehicle";
import { formatPrice, multiplyPrice } from "@/lib/format";
import { useLocale } from "@/lib/useLocale";
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
  const { t } = useTranslation();
  const locale = useLocale();
  const preferred = product.variants.find((v) => v.fitment?.fits) ?? product.variants[0];
  const [variantId, setVariantId] = useState(preferred?.id);
  const [quantity, setQuantity] = useState(defaultQuantity(product.type));
  const variant = product.variants.find((v) => v.id === variantId) ?? preferred;
  const isWheelOrSet = product.type === "wheel" || product.type === "set";
  const [viewMode, setViewMode] = useState<"photo" | "vector">("photo");
  const image = product.media[0];
  const navigate = useNavigate();
  const addToCart = useCartActions().add;

  const onAddToCart = () => {
    if (!variant) return;
    addToCart.mutate(
      {
        variantId: variant.id,
        quantity,
        product: {
          id: product.id,
          slug: product.slug,
          name: product.name,
          type: product.type,
          brand: product.brand.name,
          image: image?.image ?? null,
        },
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
        <figure className="relative">
          <div className="overflow-hidden rounded-3xl border border-white/[0.07]">
            {viewMode === "vector" || !image?.image ? (
              <div className="relative grid aspect-square w-full place-items-center overflow-hidden bg-studio p-8">
                <WheelVisual
                  type={product.type}
                  finish={variant?.finish}
                  style={product.style}
                  brake
                  spin
                  tire={product.type === "set"}
                  slug={product.slug}
                  className="size-full"
                />
              </div>
            ) : (
              <ProductPhoto src={image?.image} alt={image?.alt || product.name} eager className="aspect-square w-full" />
            )}
          </div>
          <FavoriteButton productId={product.id} isFavorite={product.is_favorite} className="absolute top-4 right-4 z-10" />

          {isWheelOrSet && image?.image && (
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => setViewMode("photo")}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-semibold transition-colors",
                  viewMode === "photo"
                    ? "bg-primary text-primary-foreground"
                    : "bg-white/10 text-muted-foreground hover:text-foreground",
                )}
              >
                {t("product.photoTab", "Foto")}
              </button>
              <button
                type="button"
                onClick={() => setViewMode("vector")}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-colors",
                  viewMode === "vector"
                    ? "bg-primary text-primary-foreground"
                    : "bg-white/10 text-muted-foreground hover:text-foreground",
                )}
              >
                <span>{t("product.studioTab", "Studio 2D")}</span>
                {variant?.finish && (
                  <span className="opacity-75">({t(`catalog.finishes.${variant.finish}`)})</span>
                )}
              </button>
            </div>
          )}

          {viewMode === "photo" && image?.credit && (
            <figcaption className="mt-2 text-[11px] text-muted-foreground">
              {image.credit_url ? (
                <a href={image.credit_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                  {t("product.photo", { credit: image.credit })}
                </a>
              ) : (
                t("product.photo", { credit: image.credit })
              )}
            </figcaption>
          )}
        </figure>

        <div className="flex flex-col gap-5">
          <div>
            <p className="text-xs font-bold tracking-[0.2em] text-primary uppercase">{product.brand.name}</p>
            <h1 className="heading-display mt-2 text-5xl md:text-6xl">{product.name}</h1>
            <ProductBadge badge={product.badge} className="mt-3" />
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
                <span className="font-display text-4xl leading-none font-extrabold">
                  {formatPrice(multiplyPrice(variant.price, quantity), locale)}
                </span>
              </div>
              <Button size="lg" disabled={addToCart.isPending} onClick={onAddToCart}>
                <ShoppingCart aria-hidden /> {t("product.addToCart")}
              </Button>
              {(product.type === "wheel" || product.type === "set") && (
                <Button asChild variant="secondary">
                  <Link
                    to={`/ai-studio?${new URLSearchParams({
                      variant: variant.id,
                      wheel: `${product.brand.name} ${product.name} ${variantSummary(variant, product.type)}`,
                    })}`}
                  >
                    <Sparkles aria-hidden /> {t("product.tryAiStudio")}
                  </Link>
                </Button>
              )}
            </div>
          )}

          {product.description && <p className="leading-relaxed text-muted-foreground">{product.description}</p>}
        </div>
      </div>

      <ReviewsSection
        productId={product.id}
        productSlug={product.slug}
        ratingAvg={product.rating_avg}
        ratingCount={product.rating_count}
      />

      {variant && (
        <div className="fixed inset-x-0 bottom-[calc(53px+env(safe-area-inset-bottom,0px))] z-20 flex items-center justify-between gap-3 border-t border-white/10 bg-background/95 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-muted-foreground">
              {variantSummary(variant, product.type)}
            </p>
            <p className="font-display text-xl leading-none font-extrabold text-foreground">
              {formatPrice(multiplyPrice(variant.price, quantity), locale)}
            </p>
          </div>
          <Button
            size="sm"
            disabled={addToCart.isPending}
            onClick={onAddToCart}
            className="shadow-md shadow-primary/25"
          >
            <ShoppingCart className="size-4" aria-hidden />
            {t("product.addToCart")}
          </Button>
        </div>
      )}
    </section>
  );
}
