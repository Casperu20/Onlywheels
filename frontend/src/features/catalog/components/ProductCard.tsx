import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { FavoriteButton } from "@/features/favorites";
import { formatPrice } from "@/lib/format";

import type { ProductListItem } from "../api";
import { variantSummary } from "../format";
import { WheelVisual } from "./WheelVisual";

export function ProductCard({ product, vehicle }: { product: ProductListItem; vehicle?: string }) {
  const { t, i18n } = useTranslation();
  const variant = product.cheapest_variant;
  const href = `/catalog/${product.slug}${vehicle ? `?vehicle=${vehicle}` : ""}`;
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-colors hover:border-[#45484f]">
      <div className="relative bg-linear-to-b from-[#202227] to-card p-6">
        {product.badge && (
          <span className="absolute top-3 left-3 rounded bg-[#35251e] px-2 py-0.5 text-[10px] font-bold text-[#ff9a70]">
            {product.badge}
          </span>
        )}
        {product.image ? (
          <img src={product.image} alt="" loading="lazy" className="mx-auto aspect-square w-3/4 object-contain" />
        ) : (
          <WheelVisual type={product.type} finish={variant?.finish} className="mx-auto w-3/4" />
        )}
      </div>
      <FavoriteButton
        productId={product.id}
        isFavorite={product.is_favorite}
        className="absolute top-3 right-3 z-10"
      />

      <div className="flex flex-1 flex-col gap-1 p-4">
        <p className="text-[10px] font-bold tracking-[1.5px] text-muted-foreground uppercase">{product.brand.name}</p>
        <h3 className="font-bold">
          <Link to={href} className="after:absolute after:inset-0 focus-visible:outline-none">
            {product.name}
          </Link>
        </h3>
        {variant && <p className="text-xs text-muted-foreground">{variantSummary(variant, product.type)}</p>}
        <p className={product.in_stock ? "text-[11px] text-success" : "text-[11px] text-muted-foreground"}>
          {product.in_stock ? t("catalog.inStock") : t("catalog.onOrder")}
        </p>
        <div className="mt-auto flex items-baseline gap-2 pt-3">
          <span className="text-xs text-muted-foreground">{t("catalog.from")}</span>
          <span className="text-lg font-extrabold">{formatPrice(product.min_price, locale)}</span>
          {product.old_price && (
            <s className="text-xs text-muted-foreground">{formatPrice(product.old_price, locale)}</s>
          )}
          <span className="text-[11px] text-muted-foreground">{t(`catalog.unit.${product.type}`)}</span>
        </div>
      </div>
    </article>
  );
}
