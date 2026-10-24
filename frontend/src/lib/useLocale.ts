import { useTranslation } from "react-i18next";

/** Intl locale matching the UI language (for prices and dates). */
export function useLocale(): string {
  const { i18n } = useTranslation();
  return i18n.language === "en" ? "en-GB" : "ro-RO";
}
