import { PackageSearch } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Skeleton } from "@/components/ui/skeleton";

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

function ProductCardSkeleton() {
  return (
    <div className="flex flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-card p-0">
      <Skeleton className="aspect-[5/4] w-full rounded-none" />
      <div className="flex flex-1 flex-col gap-2 p-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <div className="mt-auto flex items-end justify-between pt-3">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="size-9 rounded-full" />
        </div>
      </div>
    </div>
  );
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
          <ProductCardSkeleton key={i} />
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
