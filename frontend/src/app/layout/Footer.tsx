import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Logo } from "./Logo";

const ANPC_SAL = "https://anpc.ro/ce-este-sal/";

export function Footer() {
  const { t } = useTranslation();

  const columns: { title: string; links: { to: string; label: string }[] }[] = [
    {
      title: t("footer.shop"),
      links: [
        { to: "/catalog?type=wheel", label: t("catalog.types.wheel") },
        { to: "/catalog?type=tire", label: t("catalog.types.tire") },
        { to: "/catalog?type=set", label: t("catalog.types.set") },
        { to: "/catalog?type=accessory", label: t("catalog.types.accessory") },
      ],
    },
    {
      title: t("footer.help"),
      links: [
        { to: "/fitting", label: t("nav.fitting") },
        { to: "/account/garage", label: t("nav.garage") },
        { to: "/account/orders", label: t("orders.title") },
        { to: "/contact", label: t("footer.contact") },
      ],
    },
    {
      title: t("footer.legal"),
      links: [
        { to: "/legal/terms", label: t("legal.terms.title") },
        { to: "/legal/privacy", label: t("legal.privacy.title") },
        { to: "/legal/cookies", label: t("legal.cookies.title") },
      ],
    },
  ];

  return (
    <footer className="relative mt-24 overflow-hidden border-t border-white/[0.06] bg-[#0a0b0d] pb-24 lg:pb-0">
      <div aria-hidden className="racing-stripes absolute inset-x-0 top-0 h-1.5 opacity-60" />
      <div className="container-page grid gap-10 py-14 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="flex flex-col gap-4">
          <Logo small />
          <p className="max-w-xs text-sm text-muted-foreground">{t("footer.about")}</p>
        </div>
        {columns.map((column) => (
          <nav key={column.title} aria-label={column.title} className="flex flex-col gap-3">
            <h2 className="text-[11px] font-bold tracking-[0.18em] text-foreground uppercase">{column.title}</h2>
            {column.links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="text-sm text-muted-foreground transition-colors hover:text-primary"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        ))}
      </div>
      <div className="border-t border-white/[0.06]">
        <div className="container-page flex flex-col gap-3 py-6 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between">
          <span>{t("footer.tagline", { year: new Date().getFullYear() })}</span>
          <a href={ANPC_SAL} target="_blank" rel="noopener noreferrer" className="hover:text-foreground">
            {t("footer.anpc")}
          </a>
        </div>
      </div>
    </footer>
  );
}
