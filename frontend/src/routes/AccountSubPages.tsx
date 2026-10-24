import { Car, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { getErrorMessage } from "@/api/errors";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { useFavorites } from "@/features/favorites";
import { ProductGrid } from "@/features/catalog";
import {
  VehicleSelector,
  useAddMyVehicle,
  useMyVehicles,
  useRemoveMyVehicle,
  useVehicleStore,
  vehicleLabel,
} from "@/features/vehicle";

export function GaragePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: vehicles, isPending } = useMyVehicles();
  const addVehicle = useAddMyVehicle();
  const removeVehicle = useRemoveMyVehicle();
  const { active, setActive } = useVehicleStore();

  return (
    <section className="container-page flex flex-col gap-8 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight">{t("nav.garage")}</h1>
        <p className="mt-2 text-muted-foreground">{t("garage.subtitle")}</p>
      </div>

      <div className="rounded-2xl border border-border bg-card p-6">
        <h2 className="mb-4 text-sm font-semibold">{t("garage.add")}</h2>
        <VehicleSelector
          submitLabel={t("garage.save")}
          disabled={addVehicle.isPending}
          onSelect={(generation) =>
            addVehicle.mutate(
              { generation_id: generation.id, is_default: !vehicles?.length },
              {
                onSuccess: () => toast.success(t("garage.saved")),
                onError: (error) => toast.error(getErrorMessage(error, t("auth.genericError"))),
              },
            )
          }
        />
      </div>

      {isPending ? (
        <PageLoader />
      ) : vehicles?.length ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {vehicles.map((vehicle) => {
            const label = vehicleLabel(vehicle.generation, t("vehicle.present"));
            const isActive = active?.id === vehicle.generation.id;
            return (
              <li key={vehicle.id} className="flex flex-col gap-4 rounded-2xl border border-border p-5">
                <div className="flex items-start gap-3">
                  <Car className="mt-0.5 size-5 text-primary" aria-hidden />
                  <div>
                    <p className="font-semibold">{vehicle.nickname || label}</p>
                    {vehicle.nickname && <p className="text-xs text-muted-foreground">{label}</p>}
                    {!vehicle.generation.has_fitment && (
                      <p className="mt-1 text-xs text-destructive">{t("garage.noFitment")}</p>
                    )}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={isActive ? "secondary" : "default"}
                    onClick={() => {
                      setActive({ id: vehicle.generation.id, label });
                      navigate(`/catalog?type=wheel&vehicle=${vehicle.generation.id}`);
                    }}
                  >
                    {t("garage.shopFor")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={removeVehicle.isPending}
                    onClick={() => removeVehicle.mutate(vehicle.id)}
                  >
                    <Trash2 aria-hidden /> {t("garage.remove")}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-muted-foreground">{t("garage.empty")}</p>
      )}
    </section>
  );
}

export function FavoritesPage() {
  const { t } = useTranslation();
  const { data, isLoading } = useFavorites();

  return (
    <section className="container-page flex flex-col gap-8 py-10">
      <div>
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight">{t("favorites.title")}</h1>
      </div>
      <ProductGrid
        products={data?.results}
        isLoading={isLoading}
        skeletonCount={4}
        emptyTitle={t("favorites.emptyTitle")}
        emptyText={t("favorites.emptyText")}
      />
    </section>
  );
}
