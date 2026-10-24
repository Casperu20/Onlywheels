import { CircleAlert, CircleCheck } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { FitmentResult } from "../api";

export function FitmentBadge({ fitment }: { fitment: FitmentResult }) {
  const { t } = useTranslation();

  if (fitment.fits) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-success">
        <CircleCheck className="size-3.5" aria-hidden />
        {fitment.needs_hub_rings ? t("fitment.fitsWithRings") : t("fitment.fits")}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 text-xs text-destructive">
      <CircleAlert className="size-3.5" aria-hidden />
      {t("fitment.doesNotFit")}: {fitment.issues.map((issue) => t(`fitment.issues.${issue}`)).join(", ")}
    </span>
  );
}
