import { ArrowUpRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { FavoriteButton } from "@/features/favorites";
import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

import type { ProductListItem } from "../api";
import { variantSummary } from "../format";
import { ProductBadge } from "./ProductBadge";
import { ProductPhoto } from "./ProductPhoto";

export function ProductCard({ product, vehicle }: { product: ProductListItem; vehicle?: string }) {
  const { t, i18n } = useTranslation();
  const variant = product.cheapest_variant;
  const href = `/catalog/${product.slug}${vehicle ? `?vehicle=${vehicle}` : ""}`;
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-card transition-all duration-300 hover:-translate-y-1 hover:border-primary/50 hover:shadow-[0_24px_60px_-24px_rgb(255_100_45/0.55)]">
      <div className="relative aspect-[5/4] overflow-hidden">
        <ProductBadge badge={product.badge} className="absolute top-3 left-3 z-10" />
        <ProductPhoto
          src={product.image}
          type={product.type}
          finish={variant?.finish}
          style={product.style}
          slug={product.slug}
          spin
          className="size-full transition-transform duration-500 group-hover:scale-105 group-hover:rotate-2"
        />
      </div>
      <FavoriteButton productId={product.id} isFavorite={product.is_favorite} className="absolute top-3 right-3 z-10" />

      <div className="flex flex-1 flex-col gap-1.5 border-t border-white/[0.06] p-4">
        <p className="text-[10px] font-bold tracking-[0.18em] text-primary uppercase">{product.brand.name}</p>
        <h3 className="font-display text-lg leading-none font-extrabold tracking-tight [overflow-wrap:anywhere] uppercase sm:text-[22px]">
          <Link to={href} className="after:absolute after:inset-0 focus-visible:outline-none">
            {product.name}
          </Link>
        </h3>
        {variant && <p className="text-xs text-muted-foreground">{variantSummary(variant, product.type)}</p>}
        <p
          className={cn(
            "flex items-center gap-1.5 text-[11px]",
            product.in_stock ? "text-success" : "text-muted-foreground",
          )}
        >
          <span
            aria-hidden
            className={cn(
              "size-1.5 rounded-full",
              product.in_stock ? "bg-success shadow-[0_0_8px] shadow-success" : "bg-muted-foreground",
            )}
          />
          {product.in_stock ? t("catalog.inStock") : t("catalog.onOrder")}
        </p>
        <div className="mt-auto flex items-end justify-between gap-2 pt-3">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-[11px] text-muted-foreground">{t("catalog.from")}</span>
            <span className="font-display text-2xl leading-none font-extrabold">
              {formatPrice(product.min_price, locale)}
            </span>
            {product.old_price && (
              <s className="text-xs text-muted-foreground">{formatPrice(product.old_price, locale)}</s>
            )}
            <span className="text-[11px] text-muted-foreground">{t(`catalog.unit.${product.type}`)}</span>
          </div>
          <span
            aria-hidden
            className="grid size-9 shrink-0 place-items-center rounded-full border border-white/10 text-muted-foreground transition-colors group-hover:border-transparent group-hover:bg-primary group-hover:text-primary-foreground"
          >
            <ArrowUpRight className="size-4" />
          </span>
        </div>
      </div>
    </article>
  );
}
