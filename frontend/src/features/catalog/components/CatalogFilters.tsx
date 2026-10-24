import { Search, X } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { cn } from "@/lib/utils";

import { FINISHES, PRODUCT_TYPES, type ProductType } from "../api";
import { SORT_OPTIONS, toggleValue, type ProductFilters, type SortOption } from "../filters";
import { useBrands } from "../hooks";

const DIAMETERS = [15, 16, 17, 18, 19, 20];

interface CatalogFiltersProps {
  filters: ProductFilters;
  onChange: (changes: Partial<ProductFilters>) => void;
  onReset: () => void;
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs transition-colors",
        active ? "border-primary bg-primary/15 text-foreground" : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function FilterGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-[11px] font-bold tracking-[1.5px] text-muted-foreground uppercase">{title}</legend>
      <div className="flex flex-wrap gap-2">{children}</div>
    </fieldset>
  );
}

export function CatalogFilters({ filters, onChange, onReset }: CatalogFiltersProps) {
  const { t } = useTranslation();
  const { data: brands } = useBrands();
  const [search, setSearch] = useState(filters.search);
  const [priceMin, setPriceMin] = useState(filters.price_min?.toString() ?? "");
  const [priceMax, setPriceMax] = useState(filters.price_max?.toString() ?? "");

  // Keep local inputs in sync when the URL changes (back button, reset).
  useEffect(() => setSearch(filters.search), [filters.search]);
  useEffect(() => setPriceMin(filters.price_min?.toString() ?? ""), [filters.price_min]);
  useEffect(() => setPriceMax(filters.price_max?.toString() ?? ""), [filters.price_max]);

  const showWheelFilters = !filters.type || filters.type === "wheel" || filters.type === "set";
  const showDiameter = filters.type !== "accessory";

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    onChange({ search });
  };

  const submitPrice = (event: FormEvent) => {
    event.preventDefault();
    onChange({
      price_min: priceMin ? Number(priceMin) : undefined,
      price_max: priceMax ? Number(priceMax) : undefined,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div role="group" aria-label={t("catalog.type")} className="flex flex-wrap gap-2">
          <Chip active={!filters.type} onClick={() => onChange({ type: undefined })}>
            {t("catalog.all")}
          </Chip>
          {PRODUCT_TYPES.map((type: ProductType) => (
            <Chip key={type} active={filters.type === type} onClick={() => onChange({ type })}>
              {t(`catalog.types.${type}`)}
            </Chip>
          ))}
        </div>
        <form onSubmit={submitSearch} role="search" className="flex gap-2 lg:w-96">
          <Input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("catalog.searchPlaceholder")}
            aria-label={t("catalog.search")}
          />
          <Button type="submit" size="icon" aria-label={t("catalog.search")}>
            <Search aria-hidden />
          </Button>
        </form>
      </div>

      <details className="rounded-2xl border border-border p-4 lg:open:pb-6" open>
        <summary className="cursor-pointer text-sm font-semibold">{t("catalog.filters")}</summary>
        <div className="mt-4 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {brands && brands.length > 0 && (
            <FilterGroup title={t("catalog.brand")}>
              {brands.map((brand) => (
                <Chip
                  key={brand.slug}
                  active={filters.brand.includes(brand.slug)}
                  onClick={() => onChange({ brand: toggleValue(filters.brand, brand.slug) })}
                >
                  {brand.name}
                </Chip>
              ))}
            </FilterGroup>
          )}
          {showDiameter && (
            <FilterGroup title={t("catalog.diameter")}>
              {DIAMETERS.map((d) => (
                <Chip
                  key={d}
                  active={filters.diameter.includes(d)}
                  onClick={() => onChange({ diameter: toggleValue(filters.diameter, d) })}
                >
                  {d}"
                </Chip>
              ))}
            </FilterGroup>
          )}
          {showWheelFilters && (
            <FilterGroup title={t("catalog.finish")}>
              {FINISHES.map((finish) => (
                <Chip
                  key={finish}
                  active={filters.finish.includes(finish)}
                  onClick={() => onChange({ finish: toggleValue(filters.finish, finish) })}
                >
                  {t(`catalog.finishes.${finish}`)}
                </Chip>
              ))}
            </FilterGroup>
          )}
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-[11px] font-bold tracking-[1.5px] text-muted-foreground uppercase">
              {t("catalog.price")}
            </legend>
            <form onSubmit={submitPrice} className="flex items-center gap-2">
              <Input
                type="number"
                min={0}
                inputMode="numeric"
                value={priceMin}
                onChange={(e) => setPriceMin(e.target.value)}
                placeholder={t("catalog.min")}
                aria-label={t("catalog.priceMin")}
              />
              <span aria-hidden>–</span>
              <Input
                type="number"
                min={0}
                inputMode="numeric"
                value={priceMax}
                onChange={(e) => setPriceMax(e.target.value)}
                placeholder={t("catalog.max")}
                aria-label={t("catalog.priceMax")}
              />
              <Button type="submit" variant="secondary" size="sm">
                OK
              </Button>
            </form>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filters.in_stock}
                onChange={(e) => onChange({ in_stock: e.target.checked })}
                className="size-4 accent-primary"
              />
              {t("catalog.inStockOnly")}
            </label>
          </fieldset>
        </div>
      </details>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={onReset}>
          <X aria-hidden /> {t("catalog.reset")}
        </Button>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          {t("catalog.sort")}
          <NativeSelect
            className="w-auto min-w-44"
            value={filters.ordering}
            onChange={(e) => onChange({ ordering: e.target.value as SortOption })}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(`catalog.sortOptions.${option || "recommended"}`)}
              </option>
            ))}
          </NativeSelect>
        </label>
      </div>
    </div>
  );
}
