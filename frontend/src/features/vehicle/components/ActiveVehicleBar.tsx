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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-success/30 bg-success/10 p-3.5 text-sm min-w-0 max-w-full overflow-hidden">
        <span className="flex items-center gap-2 min-w-0">
          <Car className="size-4 shrink-0 text-success" aria-hidden />
          <span className="truncate">
            {t("vehicle.filteringFor")} <b className="font-semibold">{label}</b>
          </span>
        </span>
        <Button variant="ghost" size="sm" onClick={onRemove} className="shrink-0 self-start sm:self-auto">
          <X aria-hidden /> {t("vehicle.removeFilter")}
        </Button>
      </div>
    );
  }

  if (active) {
    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-border bg-card/60 p-3.5 text-sm min-w-0 max-w-full overflow-hidden">
        <span className="text-muted-foreground min-w-0 text-xs sm:text-sm">{t("vehicle.notFiltered")}</span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onApply(active.id)}
          className="h-auto py-2 px-3 whitespace-normal text-left sm:text-center max-w-full text-xs font-semibold w-full sm:w-auto"
        >
          <Car className="size-4 shrink-0" aria-hidden />
          <span className="break-words">
            {t("vehicle.showFitting", { vehicle: active.label })}
          </span>
        </Button>
      </div>
    );
  }

  return null;
}
