import { Car, ShoppingCart, User } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router";

import { Button } from "@/components/ui/button";
import { useMe } from "@/features/auth";
import { useCart } from "@/features/cart";
import { cn } from "@/lib/utils";

import { LanguageSwitcher } from "./LanguageSwitcher";
import { Logo } from "./Logo";
import { mainNav } from "./navigation";

export function Header() {
  const { t } = useTranslation();
  const { data: user } = useMe();
  const cartCount = useCart().count;

  return (
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-background/80 backdrop-blur-xl">
      <div className="container-page flex h-16 items-center justify-between gap-3 md:h-20 lg:gap-6">
        <Logo />

        <nav aria-label={t("nav.main")} className="hidden h-full items-center gap-7 lg:flex">
          {mainNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "relative flex h-full items-center gap-2 text-[13px] font-medium text-[#b8bac1] transition-colors hover:text-white",
                  isActive &&
                    "text-white after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:rounded-t after:bg-brand-gradient",
                )
              }
            >
              {t(item.labelKey)}
              {item.tagKey && (
                <span className="rounded bg-electric/15 px-1.5 py-0.5 text-[8px] font-bold tracking-[0.7px] text-electric">
                  {t(item.tagKey)}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2.5">
          <LanguageSwitcher />
          <Button asChild variant="ghost" size="icon" className="hidden sm:inline-flex">
            <Link to="/account/garage" aria-label={t("nav.garage")}>
              <Car aria-hidden />
            </Link>
          </Button>
          <Button asChild variant="ghost" size="icon">
            <Link to={user ? "/account" : "/login"} aria-label={t("nav.account")}>
              <User aria-hidden />
            </Link>
          </Button>
          <Button asChild variant="ghost" size="icon" className="relative">
            <Link to="/cart" aria-label={t("nav.cartWithCount", { count: cartCount })}>
              <ShoppingCart aria-hidden />
              <span className="absolute -top-1.5 -right-1.5 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-brand-gradient px-1 text-[10px] font-extrabold text-primary-foreground">
                {cartCount}
              </span>
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
