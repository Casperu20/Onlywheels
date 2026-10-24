import { LoaderCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

export function PageLoader() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-[40vh] place-items-center" role="status">
      <LoaderCircle className="size-8 animate-spin text-primary" aria-hidden />
      <span className="sr-only">{t("common.loading")}</span>
    </div>
  );
}
