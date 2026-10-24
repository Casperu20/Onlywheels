import { useTranslation } from "react-i18next";

export function AnnouncementBar() {
  const { t } = useTranslation();
  return (
    <div className="border-b border-border bg-[#1b1c20] text-[11px] tracking-[0.2px] text-[#b9bac1]">
      <div className="container-page flex min-h-9 items-center justify-between gap-4">
        <span>
          {t("announcement.lead")} <strong className="font-medium text-[#f2f2f3]">{t("announcement.strong")}</strong>
        </span>
        <span className="hidden sm:inline">{t("announcement.region")}</span>
      </div>
    </div>
  );
}
