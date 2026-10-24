import { Car } from "lucide-react";
import { useId, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

import type { Generation } from "../api";
import { useGenerations, useMakes, useModels } from "../hooks";

interface VehicleSelectorProps {
  onSelect: (generation: Generation) => void;
  submitLabel: string;
  submitIcon?: ReactNode;
  disabled?: boolean;
  /** Extra actions rendered next to the submit button (receives the current selection). */
  extraActions?: (generation: Generation | undefined) => ReactNode;
}

/** Make → model → generation picker ("Totul începe cu mașina ta" from the prototype). */
export function VehicleSelector({
  onSelect,
  submitLabel,
  submitIcon,
  disabled,
  extraActions,
}: VehicleSelectorProps) {
  const { t } = useTranslation();
  const ids = useId();
  const [makeId, setMakeId] = useState("");
  const [modelId, setModelId] = useState("");
  const [generationId, setGenerationId] = useState("");

  const makes = useMakes();
  const models = useModels(makeId);
  const generations = useGenerations(modelId);
  const selected = generations.data?.find((g) => g.id === generationId);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (selected) onSelect(selected);
  };

  return (
    <form onSubmit={onSubmit} className="grid items-end gap-3 md:grid-cols-[1fr_1fr_1fr_auto]">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${ids}-make`}>01 / {t("vehicle.make")}</Label>
        <NativeSelect
          id={`${ids}-make`}
          value={makeId}
          required
          onChange={(e) => {
            setMakeId(e.target.value);
            setModelId("");
            setGenerationId("");
          }}
        >
          <option value="">{t("vehicle.chooseMake")}</option>
          {makes.data?.map((make) => (
            <option key={make.id} value={make.id}>
              {make.name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${ids}-model`}>02 / {t("vehicle.model")}</Label>
        <NativeSelect
          id={`${ids}-model`}
          value={modelId}
          required
          disabled={!makeId || models.isPending}
          onChange={(e) => {
            setModelId(e.target.value);
            setGenerationId("");
          }}
        >
          <option value="">{t("vehicle.chooseModel")}</option>
          {models.data?.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name}
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor={`${ids}-generation`}>03 / {t("vehicle.generation")}</Label>
        <NativeSelect
          id={`${ids}-generation`}
          value={generationId}
          required
          disabled={!modelId || generations.isPending}
          onChange={(e) => setGenerationId(e.target.value)}
        >
          <option value="">{t("vehicle.chooseGeneration")}</option>
          {generations.data?.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name} ({g.year_from}–{g.year_to ?? t("vehicle.present")})
            </option>
          ))}
        </NativeSelect>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={!selected || disabled}>
          {submitIcon ?? <Car aria-hidden />} {submitLabel}
        </Button>
        {extraActions?.(selected)}
      </div>
    </form>
  );
}
