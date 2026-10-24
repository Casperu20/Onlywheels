import { PackageSearch } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { ProductListItem } from "../api";
import { ProductCard } from "./ProductCard";

interface ProductGridProps {
  products: ProductListItem[] | undefined;
  isLoading: boolean;
  vehicle?: string;
  skeletonCount?: number;
  emptyTitle?: string;
  emptyText?: string;
}

export function ProductGrid({
  products,
  isLoading,
  vehicle,
  skeletonCount = 8,
  emptyTitle,
  emptyText,
}: ProductGridProps) {
  const { t } = useTranslation();

  if (isLoading && !products) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4" aria-busy="true">
        {Array.from({ length: skeletonCount }, (_, i) => (
          <div key={i} className="h-80 animate-pulse rounded-2xl bg-card" />
        ))}
      </div>
    );
  }

  if (!products?.length) {
    return (
      <div className="grid place-items-center gap-3 rounded-2xl border border-dashed border-border py-16 text-center">
        <PackageSearch className="size-8 text-muted-foreground" aria-hidden />
        <p className="font-semibold">{emptyTitle ?? t("catalog.emptyTitle")}</p>
        <p className="max-w-sm text-sm text-muted-foreground">{emptyText ?? t("catalog.emptyText")}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} vehicle={vehicle} />
      ))}
    </div>
  );
}
