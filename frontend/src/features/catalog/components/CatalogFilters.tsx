import { ChevronDown, Search, SlidersHorizontal, X } from "lucide-react";
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
        "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        active
          ? "border-primary bg-primary/20 text-foreground shadow-[0_0_18px_-6px] shadow-primary"
          : "border-white/10 text-muted-foreground hover:border-white/25 hover:text-foreground",
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
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);

  // Keep local inputs in sync when the URL changes (back button, reset).
  useEffect(() => setSearch(filters.search), [filters.search]);
  useEffect(() => setPriceMin(filters.price_min?.toString() ?? ""), [filters.price_min]);
  useEffect(() => setPriceMax(filters.price_max?.toString() ?? ""), [filters.price_max]);

  const showWheelFilters = !filters.type || filters.type === "wheel" || filters.type === "set";
  const showDiameter = filters.type !== "accessory";

  const activeFilterCount =
    filters.brand.length +
    filters.diameter.length +
    filters.finish.length +
    (filters.in_stock ? 1 : 0) +
    (filters.price_min != null || filters.price_max != null ? 1 : 0);

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

  const filterContent = (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
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
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Search & Mobile Filter Trigger Bar */}
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

        <div className="flex items-center gap-2 lg:w-auto">
          <form onSubmit={submitSearch} role="search" className="flex flex-1 gap-2 lg:w-80">
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

          {/* Mobile Bottom Sheet Trigger Button */}
          <Button
            type="button"
            variant={activeFilterCount > 0 ? "default" : "secondary"}
            onClick={() => setMobileSheetOpen(true)}
            className="relative lg:hidden"
            aria-label={t("catalog.filters")}
          >
            <SlidersHorizontal className="size-4" aria-hidden />
            <span>{t("catalog.filters")}</span>
            {activeFilterCount > 0 && (
              <span className="grid size-5 place-items-center rounded-full bg-white text-[10px] font-extrabold text-black">
                {activeFilterCount}
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* Desktop Filters Details Collapsible */}
      <details className="group/filters hidden rounded-2xl border border-white/[0.08] bg-card/50 p-4 lg:block lg:open:pb-6" open>
        <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold">
          <span className="flex items-center gap-2">
            <SlidersHorizontal className="size-4 text-primary" aria-hidden />
            {t("catalog.filters")}
            {activeFilterCount > 0 && (
              <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs text-primary font-bold">
                {activeFilterCount}
              </span>
            )}
          </span>
          <ChevronDown className="size-4 transition-transform group-open/filters:rotate-180" aria-hidden />
        </summary>
        <div className="mt-4">{filterContent}</div>
      </details>

      {/* Mobile Slide-Up Bottom Sheet */}
      {mobileSheetOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileSheetOpen(false)}
            aria-hidden="true"
          />

          {/* Sheet Drawer */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t("catalog.filters")}
            className="relative z-10 max-h-[85vh] overflow-y-auto rounded-t-3xl border-t border-white/15 bg-[#14161c] p-5 shadow-2xl"
          >
            <div className="mx-auto mb-3 h-1 w-12 rounded-full bg-white/20" />
            <div className="mb-5 flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="size-5 text-primary" aria-hidden />
                <h2 className="text-lg font-bold">{t("catalog.filters")}</h2>
                {activeFilterCount > 0 && (
                  <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-bold text-primary">
                    {activeFilterCount}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {activeFilterCount > 0 && (
                  <Button variant="ghost" size="sm" onClick={onReset}>
                    {t("catalog.reset")}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setMobileSheetOpen(false)}
                  aria-label={t("common.close", "Închide")}
                >
                  <X className="size-5" />
                </Button>
              </div>
            </div>

            <div className="pb-6">{filterContent}</div>

            <div className="sticky bottom-0 -mx-5 -mb-5 border-t border-white/10 bg-[#14161c]/95 p-4 backdrop-blur">
              <Button className="w-full" size="lg" onClick={() => setMobileSheetOpen(false)}>
                {t("catalog.applyFilters", "Vezi rezultatele")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Sorting bar & Active Pills */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {activeFilterCount > 0 && (
            <Button variant="ghost" size="sm" onClick={onReset} className="text-xs text-muted-foreground hover:text-foreground">
              <X className="size-3.5" aria-hidden /> {t("catalog.reset")}
            </Button>
          )}
        </div>

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
