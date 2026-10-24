import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import {
  CatalogFilters,
  Pagination,
  ProductGrid,
  filtersToParams,
  parseFilters,
  useProducts,
  type ProductFilters,
} from "@/features/catalog";
import { ActiveVehicleBar } from "@/features/vehicle";

const PAGE_SIZE = 24;

export function CatalogPage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = parseFilters(searchParams);
  const params = filtersToParams(filters);
  const { data, isLoading, isFetching } = useProducts(params);

  const update = (changes: Partial<ProductFilters>) => {
    // Any filter change starts again from page 1.
    const next = { ...filters, page: 1, ...changes };
    setSearchParams(filtersToParams(next));
  };

  return (
    <section className="container-page flex flex-col gap-6 py-10" aria-labelledby="catalog-title">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("pages.catalog.eyebrow")}</p>
        <h1 id="catalog-title" className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">
          {t("pages.catalog.title")}
        </h1>
      </div>

      <ActiveVehicleBar
        vehicleId={filters.vehicle}
        onApply={(vehicle) => update({ vehicle })}
        onRemove={() => update({ vehicle: undefined })}
      />

      <CatalogFilters
        filters={filters}
        onChange={update}
        onReset={() => setSearchParams(filters.vehicle ? { vehicle: filters.vehicle } : {})}
      />

      <p role="status" className="text-sm text-muted-foreground">
        {data ? t("catalog.results", { count: data.count }) : "\u00a0"}
      </p>

      <div className={isFetching && data ? "opacity-60 transition-opacity" : undefined}>
        <ProductGrid products={data?.results} isLoading={isLoading} vehicle={filters.vehicle} />
      </div>

      {data && (
        <Pagination
          page={filters.page}
          pageSize={PAGE_SIZE}
          count={data.count}
          onChange={(page) => {
            setSearchParams(filtersToParams({ ...filters, page }));
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      )}

      <p className="text-center text-xs text-muted-foreground">{t("catalog.demoNote")}</p>
    </section>
  );
}
