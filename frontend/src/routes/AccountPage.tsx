import { ArrowUpRight, Car, Heart, LogOut, Package, UserRound, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import { PrivacySection, useLogout, useMe } from "@/features/auth";
import { useLocale } from "@/lib/useLocale";
import { cn } from "@/lib/utils";

const tiles: { to: string; labelKey: string; icon: LucideIcon; tone: string }[] = [
  { to: "/account/orders", labelKey: "orders.title", icon: Package, tone: "from-primary/30 text-primary" },
  { to: "/account/garage", labelKey: "nav.garage", icon: Car, tone: "from-electric/25 text-electric" },
  { to: "/account/favorites", labelKey: "favorites.title", icon: Heart, tone: "from-hot/25 text-[#ff8aa0]" },
  { to: "/account/profile", labelKey: "profile.title", icon: UserRound, tone: "from-violet-500/30 text-violet-300" },
];

export function AccountPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const logout = useLogout();

  if (!user) return null;

  return (
    <section className="container-page py-12">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("account.eyebrow")}</p>
          <h1 className="mt-3 text-5xl font-extrabold md:text-6xl">
            {t("account.greeting", { name: user.first_name || user.email })}
          </h1>
          <p className="mt-3 text-sm text-muted-foreground">
            {user.email} · {t("account.memberSince")} {new Date(user.date_joined).toLocaleDateString(locale)}
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={logout.isPending}
          onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/", { replace: true }) })}
        >
          <LogOut aria-hidden /> {t("account.logout")}
        </Button>
      </div>

      <nav aria-label={t("account.eyebrow")} className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map(({ to, labelKey, icon: Icon, tone }) => (
          <Link
            key={to}
            to={to}
            className={cn(
              "group flex min-h-36 flex-col justify-between rounded-3xl border border-white/[0.08] bg-linear-to-br to-card p-5 transition-all hover:-translate-y-1 hover:border-white/20",
              tone,
            )}
          >
            <span className="flex items-center justify-between">
              <Icon className="size-6" aria-hidden />
              <ArrowUpRight
                className="size-4 text-muted-foreground transition-colors group-hover:text-foreground"
                aria-hidden
              />
            </span>
            <span className="heading-display text-2xl text-foreground">{t(labelKey)}</span>
          </Link>
        ))}
      </nav>

      <PrivacySection user={user} />
    </section>
  );
}
