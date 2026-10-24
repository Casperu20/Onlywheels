import { Car, Heart, LogOut, Package } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import { PrivacySection, useLogout, useMe } from "@/features/auth";
import { useLocale } from "@/lib/useLocale";

export function AccountPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const navigate = useNavigate();
  const { data: user } = useMe();
  const logout = useLogout();

  if (!user) return null;

  return (
    <section className="container-page py-12">
      <p className="text-[10px] font-bold uppercase tracking-[2px] text-primary">{t("account.eyebrow")}</p>
      <h1 className="mt-3 text-3xl font-extrabold tracking-tight">
        {t("account.greeting", { name: user.first_name || user.email })}
      </h1>
      <dl className="mt-8 grid max-w-md gap-3 rounded-2xl border border-border bg-card p-6 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">{t("auth.email")}</dt>
          <dd>{user.email}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-muted-foreground">{t("account.memberSince")}</dt>
          <dd>{new Date(user.date_joined).toLocaleDateString(locale)}</dd>
        </div>
      </dl>
      <nav aria-label={t("account.eyebrow")} className="mt-6 grid max-w-xl gap-3 sm:grid-cols-3">
        <Link
          to="/account/orders"
          className="flex items-center gap-3 rounded-2xl border border-border p-4 hover:border-[#45484f]"
        >
          <Package className="size-5 text-primary" aria-hidden /> {t("orders.title")}
        </Link>
        <Link
          to="/account/garage"
          className="flex items-center gap-3 rounded-2xl border border-border p-4 hover:border-[#45484f]"
        >
          <Car className="size-5 text-primary" aria-hidden /> {t("nav.garage")}
        </Link>
        <Link
          to="/account/favorites"
          className="flex items-center gap-3 rounded-2xl border border-border p-4 hover:border-[#45484f]"
        >
          <Heart className="size-5 text-primary" aria-hidden /> {t("favorites.title")}
        </Link>
      </nav>
      <Button
        variant="secondary"
        className="mt-8"
        disabled={logout.isPending}
        onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/", { replace: true }) })}
      >
        <LogOut aria-hidden /> {t("account.logout")}
      </Button>
      <PrivacySection user={user} />
    </section>
  );
}
