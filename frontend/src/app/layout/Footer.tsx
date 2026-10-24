import { useTranslation } from "react-i18next";

import { Logo } from "./Logo";

export function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="mt-16 border-t border-border pb-20 lg:pb-0">
      <div className="container-page flex flex-col items-start justify-between gap-4 py-8 text-xs text-muted-foreground md:flex-row md:items-center">
        <Logo small />
        <span>{t("footer.tagline", { year: new Date().getFullYear() })}</span>
      </div>
    </footer>
  );
}
