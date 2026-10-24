import { useTranslation } from "react-i18next";

import { ComingSoon } from "@/components/ComingSoon";

type PlaceholderKey = "showroom" | "aiStudio";

/** Temporary pages until the feature is implemented (see docs/PROJECT_STRUCTURE.md). */
export function PlaceholderPage({ page }: { page: PlaceholderKey }) {
  const { t } = useTranslation();
  return (
    <ComingSoon
      eyebrow={t(`pages.${page}.eyebrow`)}
      title={t(`pages.${page}.title`)}
      description={t(`pages.${page}.description`)}
    />
  );
}
