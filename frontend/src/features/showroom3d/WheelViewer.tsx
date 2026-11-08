import { Box, Loader2, RotateCcw } from "lucide-react";
import { Component, lazy, Suspense, useCallback, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import type { ProductDetail } from "@/features/catalog/api";
import { ProductPhoto } from "@/features/catalog/components/ProductPhoto";

import type { CarViewModel } from "./carGeometry";
import { finishMaterial, type FinishMaterial } from "./materials";
import { wheelSpec, type WheelSize, type WheelSpec } from "./procedural";
import { supportsWebGL } from "./webgl";

const ModelCanvas = lazy(() => import("./ModelCanvas"));

interface WheelViewerProps {
  model: ProductDetail["model_3d"];
  finish: string;
  name: string;
  /** Product photo used when the device has no WebGL. */
  image: string | null;
  /** Without a GLB, a generic wheel is drawn from the selected size; `seed` (product slug) varies the spokes. */
  size?: WheelSize;
  seed?: string;
  car?: CarViewModel | null;
  view?: "wheel" | "car";
  onViewChange?: (view: "wheel" | "car") => void;
}

const NOOP_VIEW_CHANGE = () => {};

export function WheelViewer({
  model,
  finish,
  name,
  image,
  size,
  seed = name,
  car = null,
  view = "wheel",
  onViewChange = NOOP_VIEW_CHANGE,
}: WheelViewerProps) {
  const { t } = useTranslation();
  const [webgl] = useState(supportsWebGL);
  const [attempt, setAttempt] = useState(0);
  const finishMaterials = model?.finish_materials;
  const material = useMemo(() => finishMaterial(finishMaterials, finish), [finishMaterials, finish]);
  const { diameterIn, widthIn, pcd } = size ?? {};
  const spec = useMemo(() => wheelSpec({ diameterIn, widthIn, pcd, seed }), [diameterIn, widthIn, pcd, seed]);

  if (!webgl) return <Fallback image={image} name={name} title={t("showroom.noWebglTitle")} text={t("showroom.noWebgl")} />;

  const url = model?.glb_file ?? null;
  const activeCar = view === "car" ? car : null;
  const retry = async () => {
    const urls = [url, activeCar?.glb_file].filter((value): value is string => Boolean(value));
    if (urls.length) {
      const { clearModel } = await import("./ModelCanvas");
      urls.forEach((value) => clearModel(value));
    }
    setAttempt((value) => value + 1);
  };

  return (
    <div className="space-y-2">
      <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-border bg-gradient-to-b from-muted/40 to-card">
        <Stage
          key={`${url ?? "generic"}#${activeCar?.glb_file ?? "wheel-only"}#${attempt}`}
          url={url}
          car={activeCar}
          spec={spec}
          material={material}
          label={t("showroom.viewerLabel", { name })}
          onRetry={retry}
          onBackToWheelOnly={() => onViewChange("wheel")}
        />
        {!url && (
          <div className="pointer-events-none absolute inset-x-3 top-3 flex gap-2 rounded-xl bg-background/80 p-3 text-xs backdrop-blur">
            <Box className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            <div>
              <p className="font-semibold">{t("showroom.genericTitle")}</p>
              <p className="mt-0.5 text-muted-foreground">{t("showroom.generic")}</p>
            </div>
          </div>
        )}
      </div>
      {activeCar && (
        <p className="text-xs text-muted-foreground">
          {activeCar.source_url ? (
            <a href={activeCar.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-4">
              {activeCar.attribution}
            </a>
          ) : (
            activeCar.attribution
          )}
        </p>
      )}
    </div>
  );
}

function Stage({
  url,
  spec,
  car,
  material,
  label,
  onRetry,
  onBackToWheelOnly,
}: {
  url: string | null;
  car: CarViewModel | null;
  spec: WheelSpec;
  material: FinishMaterial;
  label: string;
  onRetry: () => void;
  onBackToWheelOnly: () => void;
}) {
  const { t } = useTranslation();
  const [ready, setReady] = useState(false);
  const onReady = useCallback(() => setReady(true), []);

  return (
    <ViewerErrorBoundary
      fallback={
        <div role="alert" className="absolute inset-0 grid place-content-center gap-3 p-6 text-center text-sm">
          <p className="font-semibold">{t("showroom.loadError")}</p>
          <Button variant="secondary" onClick={onRetry} className="mx-auto">
            <RotateCcw aria-hidden /> {t("showroom.retry")}
          </Button>
          {car && (
            <Button variant="ghost" onClick={onBackToWheelOnly} className="mx-auto">
              {t("showroom.backToWheelOnly")}
            </Button>
          )}
        </div>
      }
    >
      <Suspense fallback={null}>
        <ModelCanvas url={url} car={car} spec={spec} material={material} label={label} onReady={onReady} />
      </Suspense>
      {!ready && (
        <div role="status" className="absolute inset-0 grid place-content-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="mx-auto size-6 animate-spin" aria-hidden />
          {t("showroom.loading")}
        </div>
      )}
    </ViewerErrorBoundary>
  );
}

class ViewerErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function Fallback({ image, name, title, text }: { image: string | null; name: string; title: string; text: string }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card">
      <ProductPhoto src={image} alt={name} className="aspect-square w-full" eager />
      <div className="flex gap-3 p-4 text-sm">
        <Box className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-muted-foreground">{text}</p>
        </div>
      </div>
    </div>
  );
}
