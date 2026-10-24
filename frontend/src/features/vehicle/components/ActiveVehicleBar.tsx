import { Car, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

import { vehicleLabel } from "../format";
import { useGeneration } from "../hooks";
import { useVehicleStore } from "../store";

interface ActiveVehicleBarProps {
  /** Vehicle currently applied as filter (from the URL). */
  vehicleId?: string;
  onApply: (vehicleId: string) => void;
  onRemove: () => void;
}

/** Catalog banner: shows the car the results are filtered for, or offers to filter by the saved one. */
export function ActiveVehicleBar({ vehicleId, onApply, onRemove }: ActiveVehicleBarProps) {
  const { t } = useTranslation();
  const active = useVehicleStore((s) => s.active);
  const { data: generation } = useGeneration(vehicleId);

  if (vehicleId) {
    const label = generation ? vehicleLabel(generation, t("vehicle.present")) : "…";
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-success/30 bg-success/10 px-4 py-3 text-sm">
        <span className="flex items-center gap-2">
          <Car className="size-4 text-success" aria-hidden />
          {t("vehicle.filteringFor")} <b>{label}</b>
        </span>
        <Button variant="ghost" size="sm" onClick={onRemove}>
          <X aria-hidden /> {t("vehicle.removeFilter")}
        </Button>
      </div>
    );
  }

  if (active) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border px-4 py-3 text-sm">
        <span className="text-muted-foreground">{t("vehicle.notFiltered")}</span>
        <Button variant="secondary" size="sm" onClick={() => onApply(active.id)}>
          <Car aria-hidden /> {t("vehicle.showFitting", { vehicle: active.label })}
        </Button>
      </div>
    );
  }

  return null;
}
