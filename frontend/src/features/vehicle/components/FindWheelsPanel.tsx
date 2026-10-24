import { Grid3x3, Save } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { getErrorMessage } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { useMe } from "@/features/auth";

import { vehicleLabel } from "../format";
import { useAddMyVehicle } from "../hooks";
import { useVehicleStore } from "../store";
import { VehicleSelector } from "./VehicleSelector";

/** Home page block: pick a car, then jump to the catalog filtered for it. */
export function FindWheelsPanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const setActive = useVehicleStore((s) => s.setActive);
  const active = useVehicleStore((s) => s.active);
  const addVehicle = useAddMyVehicle();

  return (
    <div
      id="vehicle-search"
      className="mt-7 rounded-2xl border border-[#34363b] bg-linear-to-r from-[#222429] to-card p-6"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{t("vehicle.panelTitle")}</h2>
        <Link to="/account/garage" className="text-xs text-primary hover:underline">
          {t("nav.garage")} →
        </Link>
      </div>
      <VehicleSelector
        submitLabel={t("vehicle.findWheels")}
        submitIcon={<Grid3x3 aria-hidden />}
        onSelect={(generation) => {
          setActive({ id: generation.id, label: vehicleLabel(generation, t("vehicle.present")) });
          navigate(`/catalog?type=wheel&vehicle=${generation.id}`);
        }}
        extraActions={(generation) =>
          user && generation ? (
            <Button
              type="button"
              variant="secondary"
              disabled={addVehicle.isPending}
              onClick={() =>
                addVehicle.mutate(
                  { generation_id: generation.id },
                  {
                    onSuccess: () => toast.success(t("garage.saved")),
                    onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
                  },
                )
              }
            >
              <Save aria-hidden /> {t("garage.save")}
            </Button>
          ) : null
        }
      />
      <p className="mt-3 text-xs text-muted-foreground">
        {active ? t("vehicle.activeHint", { vehicle: active.label }) : t("vehicle.demoHint")}
      </p>
    </div>
  );
}
