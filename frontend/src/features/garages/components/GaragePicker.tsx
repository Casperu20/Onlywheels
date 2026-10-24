import { useId } from "react";
import { useTranslation } from "react-i18next";

import { PageLoader } from "@/components/PageLoader";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

import { isoDate, useGarages, useSlots } from "../api";
import { GarageCard } from "./GarageCard";

export interface GarageSelection {
  garageId?: string;
  garageSlug?: string;
  date: string;
  slotStart?: string;
}

interface GaragePickerProps {
  value: GarageSelection;
  onChange: (value: GarageSelection) => void;
  error?: string;
}

/** Choose a partner garage, a day and a free fitting slot. */
export function GaragePicker({ value, onChange, error }: GaragePickerProps) {
  const { t, i18n } = useTranslation();
  const dateId = useId();
  const { data: garages, isPending } = useGarages();
  const slots = useSlots(value.garageSlug, value.date);
  const locale = i18n.language === "en" ? "en-GB" : "ro-RO";

  if (isPending) return <PageLoader />;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 md:grid-cols-2">
        {garages?.map((garage) => (
          <GarageCard
            key={garage.id}
            garage={garage}
            selected={garage.id === value.garageId}
            onSelect={() => onChange({ ...value, garageId: garage.id, garageSlug: garage.slug, slotStart: undefined })}
          />
        ))}
      </div>

      {value.garageSlug && (
        <div className="flex flex-col gap-3">
          <div className="flex max-w-xs flex-col gap-1.5">
            <Label htmlFor={dateId}>{t("garages.date")}</Label>
            <Input
              id={dateId}
              type="date"
              min={isoDate(1)}
              max={isoDate(14)}
              value={value.date}
              onChange={(e) => onChange({ ...value, date: e.target.value, slotStart: undefined })}
            />
          </div>
          {slots.isPending ? (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : slots.data?.length ? (
            <div role="radiogroup" aria-label={t("garages.slot")} className="flex flex-wrap gap-2">
              {slots.data.map((slot) => (
                <button
                  key={slot.start}
                  type="button"
                  role="radio"
                  aria-checked={value.slotStart === slot.start}
                  onClick={() => onChange({ ...value, slotStart: slot.start })}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-sm",
                    value.slotStart === slot.start
                      ? "border-primary bg-primary/15"
                      : "border-border hover:border-[#45484f]",
                  )}
                >
                  {new Date(slot.start).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("garages.noSlots")}</p>
          )}
        </div>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
