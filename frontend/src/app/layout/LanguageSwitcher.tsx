import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES } from "@/i18n";
import { cn } from "@/lib/utils";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const current = i18n.resolvedLanguage ?? "ro";

  return (
    <div role="group" aria-label={t("header.language")} className="flex rounded-[10px] border border-border p-0.5">
      {SUPPORTED_LANGUAGES.map((lng) => (
        <button
          key={lng}
          type="button"
          onClick={() => void i18n.changeLanguage(lng)}
          aria-pressed={current === lng}
          className={cn(
            "rounded-lg px-2 py-1 text-[11px] font-bold uppercase",
            current === lng ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {lng}
        </button>
      ))}
    </div>
  );
}
