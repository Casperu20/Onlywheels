import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";

import { cn } from "@/lib/utils";

import { mobileNav } from "./navigation";

export function MobileNav() {
  const { t } = useTranslation();
  return (
    <nav
      aria-label={t("nav.mobile")}
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg lg:hidden"
    >
      {mobileNav.map(({ to, labelKey, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center gap-1 py-2.5 text-[10px] text-muted-foreground",
              isActive && "text-primary",
            )
          }
        >
          <Icon className="size-5" aria-hidden />
          {t(labelKey)}
        </NavLink>
      ))}
    </nav>
  );
}
