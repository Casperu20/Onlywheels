import { Sparkles } from "lucide-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";

import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import type { ProductDetail, ProductListItem } from "@/features/catalog/api";
import { variantSummary } from "@/features/catalog/format";
import { useProduct, useProducts } from "@/features/catalog/hooks";
import { useGeneration } from "@/features/vehicle/hooks";
import { useVehicleStore } from "@/features/vehicle/store";
import { formatPrice } from "@/lib/format";

import { useCarModels, type CarModel } from "./api";
import { WheelViewer } from "./WheelViewer";

const LIST_PARAMS = { type: "wheel", page_size: "100" };

export function ShowroomPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const products = useProducts(LIST_PARAMS);
  const carModels = useCarModels();
  const activeVehicle = useVehicleStore((state) => state.active);
  const activeGeneration = useGeneration(activeVehicle?.id);
  const slug = searchParams.get("product") ?? products.data?.results[0]?.slug ?? null;

  let body;
  if (slug) {
    body = (
      <ShowroomStage
        slug={slug}
        options={products.data?.results ?? []}
        cars={carModels.data ?? []}
        carModelsError={carModels.isError}
        preferredVehicleModelId={activeGeneration.data?.model.id}
      />
    );
  }
  else if (products.isPending) body = <PageLoader />;
  else if (products.isError) body = <ProductError />;
  else
    body = (
      <div className="max-w-xl rounded-2xl border border-border bg-card p-6">
        <p className="font-semibold">{t("showroom.noModelsTitle")}</p>
        <p className="mt-2 text-sm text-muted-foreground">{t("showroom.noModels")}</p>
        <Button asChild variant="secondary" className="mt-4">
          <Link to="/catalog?type=wheel">{t("showroom.browseCatalog")}</Link>
        </Button>
      </div>
    );

  return (
    <section className="container-page py-10">
      <header className="mb-8 max-w-2xl">
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("pages.showroom.eyebrow")}</p>
        <h1 className="heading-display mt-2 text-4xl md:text-5xl">{t("pages.showroom.title")}</h1>
        <p className="mt-3 text-muted-foreground">{t("pages.showroom.description")}</p>
      </header>
      {body}
    </section>
  );
}

function ProductError() {
  const { t } = useTranslation();
  return (
    <div role="alert" className="max-w-xl rounded-2xl border border-border bg-card p-6 text-sm">
      <p className="font-semibold">{t("showroom.productError")}</p>
      <Link to="/catalog?type=wheel" className="mt-2 inline-block text-primary underline-offset-4 hover:underline">
        {t("showroom.browseCatalog")}
      </Link>
    </div>
  );
}

const displayName = (product: Pick<ProductListItem, "name" | "brand">) => `${product.brand.name} ${product.name}`;

function ShowroomStage({
  slug,
  options,
  cars,
  carModelsError,
  preferredVehicleModelId,
}: {
  slug: string;
  options: ProductListItem[];
  cars: CarModel[];
  carModelsError: boolean;
  preferredVehicleModelId?: string;
}) {
  const product = useProduct(slug);
  if (product.isError) return <ProductError />;
  if (!product.data) return <PageLoader />;
  return (
    <Configurator
      key={slug}
      product={product.data}
      options={options}
      cars={cars}
      carModelsError={carModelsError}
      preferredVehicleModelId={preferredVehicleModelId}
    />
  );
}

function Configurator({
  product,
  options,
  cars,
  carModelsError,
  preferredVehicleModelId,
}: {
  product: ProductDetail;
  options: ProductListItem[];
  cars: CarModel[];
  carModelsError: boolean;
  preferredVehicleModelId?: string;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";
  const ids = { product: useId(), finish: useId(), size: useId(), car: useId() };
  const [searchParams, setSearchParams] = useSearchParams();

  const isPreferredCar = (car: CarModel) =>
    Boolean(preferredVehicleModelId) && car.vehicle_model?.id === preferredVehicleModelId;
  const preferredCar = cars.find(isPreferredCar);
  const selectedCar =
    cars.find((car) => car.slug === searchParams.get("car")) ?? preferredCar ?? cars[0] ?? null;
  const view = searchParams.get("view") === "car" && selectedCar ? "car" : "wheel";
  const updateParams = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setSearchParams(next, { replace: true, preventScrollReset: true });
  };
  const selectView = (nextView: "wheel" | "car") => {
    updateParams(
      nextView === "car"
        ? { view: "car", car: selectedCar?.slug ?? null }
        : { view: null, car: null },
    );
  };

  const variants = product.variants;
  const variant =
    variants.find((v) => v.id === searchParams.get("variant")) ??
    variants.find((v) => v.id === product.cheapest_variant?.id) ??
    variants[0];
  const finishes = [...new Set(variants.map((v) => v.finish).filter(Boolean))];
  const finish = variant?.finish || Object.keys(product.model_3d?.finish_materials ?? {})[0] || "silver";
  const sizes = variants.filter((v) => v.finish === variant?.finish);
  const choices = options.some((o) => o.slug === product.slug) ? options : [product, ...options];

  const selectVariant = (id: string) => updateParams({ product: product.slug, variant: id });

  const aiStudioLink = variant
    ? `/ai-studio?${new URLSearchParams({ variant: variant.id, wheel: `${displayName(product)} ${variantSummary(variant, product.type)}` })}`
    : "/ai-studio";

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div>
        {carModelsError && (
          <p role="status" className="mb-3 text-sm text-muted-foreground">
            {t("showroom.carModelsError")}
          </p>
        )}
        {cars.length > 0 && (
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <div role="group" aria-label={t("showroom.viewMode")} className="flex gap-2">
              <Button
                type="button"
                variant={view === "wheel" ? "default" : "secondary"}
                aria-pressed={view === "wheel"}
                onClick={() => selectView("wheel")}
              >
                {t("showroom.wheelOnly")}
              </Button>
              <Button
                type="button"
                variant={view === "car" ? "default" : "secondary"}
                aria-pressed={view === "car"}
                onClick={() => selectView("car")}
              >
                {t("showroom.onCar")}
              </Button>
            </div>
            {view === "car" && selectedCar && (
              <div className="min-w-52 space-y-2">
                <Label htmlFor={ids.car}>{t("showroom.carModel")}</Label>
                <NativeSelect
                  id={ids.car}
                  value={selectedCar.slug}
                  onChange={(event) => updateParams({ view: "car", car: event.target.value })}
                >
                  {cars.map((car) => (
                    <option key={car.slug} value={car.slug}>
                      {car.name}
                      {isPreferredCar(car) ? ` (${t("showroom.yourCar")})` : ""}
                    </option>
                  ))}
                </NativeSelect>
              </div>
            )}
          </div>
        )}
        <WheelViewer
          model={product.model_3d}
          finish={finish}
          name={displayName(product)}
          image={product.image}
          seed={product.slug}
          size={{ diameterIn: variant?.diameter_in, widthIn: variant?.width_in, pcd: variant?.pcd }}
          car={view === "car" ? selectedCar : null}
          view={view}
          onViewChange={selectView}
        />
        <p className="mt-2 text-xs text-muted-foreground">{t("showroom.hint")}</p>
      </div>

      <div className="h-fit space-y-5 rounded-2xl border border-border bg-card p-6">
        <div className="space-y-2">
          <Label htmlFor={ids.product}>{t("showroom.product")}</Label>
          <NativeSelect
            id={ids.product}
            value={product.slug}
            onChange={(event) => updateParams({ product: event.target.value, variant: null })}
          >
            {choices.map((option) => (
              <option key={option.slug} value={option.slug}>
                {displayName(option)}
              </option>
            ))}
          </NativeSelect>
        </div>

        {finishes.length > 0 && (
          <div className="space-y-2">
            <Label htmlFor={ids.finish}>{t("showroom.finish")}</Label>
            <NativeSelect
              id={ids.finish}
              value={variant?.finish ?? ""}
              onChange={(event) => {
                const next = variants.find((v) => v.finish === event.target.value);
                if (next) selectVariant(next.id);
              }}
            >
              {finishes.map((value) => (
                <option key={value} value={value}>
                  {t(`catalog.finishes.${value}`)}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}

        {sizes.length > 0 && variant && (
          <div className="space-y-2">
            <Label htmlFor={ids.size}>{t("showroom.size")}</Label>
            <NativeSelect id={ids.size} value={variant.id} onChange={(event) => selectVariant(event.target.value)}>
              {sizes.map((v) => (
                <option key={v.id} value={v.id}>
                  {variantSummary(v, product.type)}
                </option>
              ))}
            </NativeSelect>
          </div>
        )}

        {variant && <p className="text-2xl font-bold">{formatPrice(variant.price, locale)}</p>}
        <p className="text-xs text-muted-foreground">{t("showroom.illustrative")}</p>

        <div className="flex flex-col gap-2">
          <Button asChild>
            <Link to={`/catalog/${product.slug}`}>{t("showroom.viewProduct")}</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to={aiStudioLink}>
              <Sparkles aria-hidden /> {t("product.tryAiStudio")}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
