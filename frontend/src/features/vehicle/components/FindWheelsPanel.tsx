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
      className="relative mt-8 rounded-3xl bg-linear-to-r from-primary/70 via-white/10 to-electric/50 p-px shadow-[0_30px_80px_-40px_rgb(255_100_45/0.6)]"
    >
      <div className="rounded-[calc(1.5rem-1px)] bg-[#121418]/95 p-5 sm:p-6 md:p-7 backdrop-blur min-w-0 overflow-hidden">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <h2 className="heading-display text-2xl md:text-3xl">{t("vehicle.panelTitle")}</h2>
          <Link to="/account/garage" className="text-xs font-semibold text-primary hover:underline">
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
    </div>
  );
}
