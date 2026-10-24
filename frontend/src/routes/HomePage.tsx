import { ArrowRight, Box, CreditCard, ShieldCheck, Wrench, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";
import { ProductGrid, WheelVisual, useProducts } from "@/features/catalog";
import { PRODUCT_TYPES } from "@/features/catalog/api";
import { FindWheelsPanel } from "@/features/vehicle";

const FEATURED_PARAMS = { featured: "true", page_size: "8" };

const benefits: { key: string; icon: LucideIcon }[] = [
  { key: "fit", icon: ShieldCheck },
  { key: "preview", icon: Box },
  { key: "payment", icon: CreditCard },
  { key: "fitting", icon: Wrench },
];

export function HomePage() {
  const { t } = useTranslation();
  const featured = useProducts(FEATURED_PARAMS);

  return (
    <>
      <section className="container-page pt-10 md:pt-12" aria-labelledby="hero-title">
        <div className="grid min-h-[360px] items-center gap-8 md:grid-cols-[0.95fr_1.2fr]">
          <div>
            <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[2px] text-primary before:h-px before:w-6 before:bg-primary">
              {t("home.eyebrow")}
            </p>
            <h1
              id="hero-title"
              className="mt-6 mb-5 text-[clamp(40px,4.6vw,65px)] leading-[1.05] font-extrabold tracking-[-2.8px]"
            >
              {t("home.title1")}
              <br />
              {t("home.title2")} <em className="not-italic text-primary">{t("home.titleAccent")}</em>
            </h1>
            <p className="mb-7 max-w-sm leading-relaxed text-muted-foreground">{t("home.lead")}</p>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link to="/catalog">
                  {t("home.ctaCatalog")} <ArrowRight aria-hidden />
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link to="/showroom">
                  <Box aria-hidden /> {t("home.ctaShowroom")}
                </Link>
              </Button>
            </div>
          </div>
          <div className="relative hidden aspect-[16/9] items-center justify-center md:flex">
            <span
              aria-hidden
              className="absolute top-6 left-0 text-[clamp(50px,7vw,100px)] font-black tracking-[-6px] text-white/[0.02]"
            >
              YOUR NEXT LOOK
            </span>
            <img src="/onlywheels-logo.svg" alt="" className="w-1/2 opacity-90 drop-shadow-2xl" />
          </div>
        </div>

        <FindWheelsPanel />

        <ul className="mt-8 grid grid-cols-2 gap-4 rounded-2xl border border-border p-5 md:grid-cols-4">
          {benefits.map(({ key, icon: Icon }) => (
            <li key={key} className="flex items-start gap-3">
              <Icon className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
              <div>
                <b className="block text-sm">{t(`home.benefits.${key}.title`)}</b>
                <small className="text-xs text-muted-foreground">{t(`home.benefits.${key}.text`)}</small>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="container-page mt-16" aria-labelledby="category-title">
        <h2 id="category-title" className="text-2xl font-extrabold tracking-tight md:text-3xl">
          {t("home.categoriesTitle")}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("home.categoriesText")}</p>
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          {PRODUCT_TYPES.map((type) => (
            <Link
              key={type}
              to={`/catalog?type=${type}`}
              className="group flex items-center justify-between gap-3 rounded-2xl border border-border bg-card p-5 hover:border-[#45484f]"
            >
              <span>
                <b className="block">{t(`catalog.types.${type}`)}</b>
                <small className="text-xs text-muted-foreground">{t(`home.categories.${type}`)}</small>
              </span>
              <WheelVisual type={type} finish={type === "set" ? "black" : "silver"} className="w-14 shrink-0" />
            </Link>
          ))}
        </div>
      </section>

      <section className="container-page mt-16" aria-labelledby="featured-title">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="featured-title" className="text-2xl font-extrabold tracking-tight md:text-3xl">
              {t("home.featuredTitle")}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">{t("home.featuredText")}</p>
          </div>
          <Link to="/catalog" className="text-sm text-primary hover:underline">
            {t("home.viewAll")} →
          </Link>
        </div>
        <ProductGrid products={featured.data?.results} isLoading={featured.isLoading} skeletonCount={4} />
      </section>
    </>
  );
}
