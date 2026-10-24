import { MapPin, Phone } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";

import type { Garage } from "../api";

export function GarageCard({
  garage,
  selected,
  onSelect,
}: {
  garage: Garage;
  selected?: boolean;
  onSelect?: () => void;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";
  const dayName = (weekday: number) =>
    new Date(2024, 0, 1 + weekday).toLocaleDateString(locale, { weekday: "short" }); // 2024-01-01 = Monday
  const days = [...garage.working_days].sort().map(dayName);

  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{garage.name}</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin className="size-3.5" aria-hidden /> {garage.address}, {garage.city}
          </p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Phone className="size-3.5" aria-hidden /> {garage.phone}
          </p>
        </div>
        <div className="text-right">
          <p className="font-bold">{formatPrice(garage.fitting_price, locale)}</p>
          <p className="text-[11px] text-muted-foreground">{t("garages.perSet")}</p>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        {days.join(", ")} · {garage.opens_at.slice(0, 5)}–{garage.closes_at.slice(0, 5)}
      </p>
    </>
  );

  if (!onSelect) {
    return <div className="rounded-2xl border border-border bg-card p-5">{content}</div>;
  }
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "w-full rounded-2xl border p-5 text-left transition-colors",
        selected ? "border-primary bg-primary/5" : "border-border bg-card hover:border-[#45484f]",
      )}
    >
      {content}
    </button>
  );
}
