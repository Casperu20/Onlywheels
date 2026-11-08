import { ArrowRight, ArrowUpRight, Box, Check, CreditCard, ShieldCheck, Sparkles, Wrench, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import wheelPhoto from "@/assets/demo/bbs-ch-r.jpg";
import credits from "@/assets/demo/credits.json";
import heroPhoto from "@/assets/demo/hero.jpg";
import accessoryPhoto from "@/assets/demo/kit-prezoane.jpg";
import tirePhoto from "@/assets/demo/michelin-pilot-sport-5.jpg";
import fittingPhoto from "@/assets/demo/set-sport-graphite.jpg";
import setPhoto from "@/assets/demo/set-urban-silver.jpg";
import { Button } from "@/components/ui/button";
import { ProductGrid, useProducts } from "@/features/catalog";
import { PRODUCT_TYPES, type ProductType } from "@/features/catalog/api";
import { FindWheelsPanel } from "@/features/vehicle";
import { cn } from "@/lib/utils";

const FEATURED_PARAMS = { featured: "true", page_size: "8" };

type PhotoName = keyof typeof credits;

const creditText = (name: PhotoName) => `${credits[name].author}, ${credits[name].license}`;

const benefits: { key: string; icon: LucideIcon; tone: string }[] = [
  { key: "fit", icon: ShieldCheck, tone: "bg-primary/15 text-primary" },
  { key: "preview", icon: Box, tone: "bg-electric/15 text-electric" },
  { key: "payment", icon: CreditCard, tone: "bg-violet-400/15 text-violet-300" },
  { key: "fitting", icon: Wrench, tone: "bg-success/15 text-success" },
];

const categoryTiles: Record<ProductType, { photo: string; credit: PhotoName }> = {
  wheel: { photo: wheelPhoto, credit: "bbs-ch-r" },
  tire: { photo: tirePhoto, credit: "michelin-pilot-sport-5" },
  set: { photo: setPhoto, credit: "set-urban-silver" },
  accessory: { photo: accessoryPhoto, credit: "kit-prezoane" },
};

export function HomePage() {
  const { t } = useTranslation();
  const featured = useProducts(FEATURED_PARAMS);
  const results = featured.data?.results;
  // Full rows only: 8 when there are enough, otherwise 4.
  const featuredProducts = results && results.length >= 8 ? results.slice(0, 8) : results?.slice(0, 4);

  return (
    <>
      <section className="relative overflow-hidden" aria-labelledby="hero-title">
        <div aria-hidden className="bg-blueprint pointer-events-none absolute inset-0" />
        <div className="container-page relative grid items-center gap-4 pt-10 pb-4 md:grid-cols-[1fr_1.05fr] md:pt-14">
          <div className="relative z-10">
            <p className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-[11px] font-bold tracking-[0.18em] text-[#ffb08f] uppercase">
              <span aria-hidden className="size-1.5 animate-pulse rounded-full bg-primary" />
              {t("home.eyebrow")}
            </p>
            <h1 id="hero-title" className="heading-display mt-6 text-[clamp(54px,7.6vw,108px)]">
              {t("home.title1")}
              <br />
              {t("home.title2")} <em className="text-gradient pr-3">{t("home.titleAccent")}</em>
            </h1>
            <p className="mt-6 max-w-md text-base leading-relaxed text-muted-foreground md:text-lg">{t("home.lead")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/catalog">
                  {t("home.ctaCatalog")} <ArrowRight aria-hidden />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary">
                <Link to="/showroom">
                  <Box aria-hidden /> {t("home.ctaShowroom")}
                </Link>
              </Button>
            </div>
            <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-white/10 pt-6">
              {(["fit", "fitting", "delivery"] as const).map((key) => (
                <div key={key} className="flex flex-col-reverse gap-1">
                  <dt className="text-[11px] leading-tight text-muted-foreground">{t(`home.stats.${key}.label`)}</dt>
                  <dd className="font-display text-3xl leading-none font-extrabold">{t(`home.stats.${key}.value`)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <HeroStage />
        </div>

        <div className="container-page relative">
          <FindWheelsPanel />
          <ul className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            {benefits.map(({ key, icon: Icon, tone }) => (
              <li
                key={key}
                className="flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-card/60 p-4 backdrop-blur"
              >
                <span className={cn("grid size-10 shrink-0 place-items-center rounded-xl", tone)}>
                  <Icon className="size-5" aria-hidden />
                </span>
                <div>
                  <b className="block text-sm">{t(`home.benefits.${key}.title`)}</b>
                  <small className="text-xs text-muted-foreground">{t(`home.benefits.${key}.text`)}</small>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="container-page mt-20" aria-labelledby="category-title">
        <SectionHeading index="01" id="category-title" title={t("home.categoriesTitle")} text={t("home.categoriesText")} />
        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {PRODUCT_TYPES.map((type) => (
            <Link
              key={type}
              to={`/catalog?type=${type}`}
              className="group relative flex min-h-48 flex-col justify-between overflow-hidden rounded-3xl border border-white/[0.08] bg-card p-5 transition-all hover:-translate-y-1 hover:border-white/20 md:min-h-56"
            >
              <img
                src={categoryTiles[type].photo}
                alt=""
                loading="lazy"
                className="absolute inset-0 size-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <span aria-hidden className="absolute inset-0 bg-linear-to-b from-black/85 via-black/30 to-black/60" />
              <span className="relative z-10">
                <b className="heading-display block text-3xl md:text-4xl">{t(`catalog.types.${type}`)}</b>
                <small className="mt-1 block max-w-[75%] text-xs text-white/75">
                  {t(`home.categories.${type}`)}
                </small>
              </span>
              <span className="relative z-10 grid size-9 place-items-center rounded-full bg-white/15 backdrop-blur transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <ArrowUpRight className="size-4" aria-hidden />
              </span>
              <small className="absolute right-3 bottom-2 z-10 max-w-[60%] truncate text-[9px] text-white/55">
                {t("product.photo", { credit: creditText(categoryTiles[type].credit) })}
              </small>
            </Link>
          ))}
        </div>
      </section>

      <section className="container-page mt-20 grid gap-4 lg:grid-cols-[1.35fr_1fr]" aria-label={t("home.promo.label")}>
        <Link
          to="/fitting"
          className="group bg-brand-gradient relative flex min-h-72 flex-col justify-end overflow-hidden rounded-3xl p-7 text-primary-foreground md:p-9"
        >
          <span aria-hidden className="racing-stripes absolute inset-y-0 left-0 w-1/2 opacity-60" />
          <img
            src={fittingPhoto}
            alt=""
            loading="lazy"
            className="absolute top-0 right-0 h-1/2 w-full object-cover [mask-image:linear-gradient(to_bottom,black_45%,transparent)] md:h-full md:w-[55%] md:[mask-image:linear-gradient(to_left,black_55%,transparent)]"
          />
          <small className="absolute top-2 right-3 z-10 text-[9px] text-white/70">
            {t("product.photo", { credit: creditText("set-sport-graphite") })}
          </small>
          <span className="relative z-10 flex max-w-md flex-col gap-3">
            <span className="text-[11px] font-extrabold tracking-[0.2em] uppercase opacity-80">
              {t("home.promo.fittingEyebrow")}
            </span>
            <b className="heading-display text-4xl md:text-5xl">{t("home.promo.fittingTitle")}</b>
            <span className="text-sm font-medium opacity-85">{t("home.promo.fittingText")}</span>
            <span className="mt-2 inline-flex w-fit items-center gap-2 rounded-full bg-[#140a05] px-4 py-2 text-sm font-bold text-white transition-transform group-hover:translate-x-1">
              {t("home.promo.fittingCta")} <ArrowRight className="size-4" aria-hidden />
            </span>
          </span>
        </Link>
        <div className="grid gap-4">
          <TeaserCard
            to="/showroom"
            icon={Box}
            className="bg-[radial-gradient(ellipse_at_90%_10%,rgb(56_214_255/0.35),transparent_60%)]"
            title={t("home.promo.showroomTitle")}
            text={t("home.promo.showroomText")}
            soon={t("home.promo.soon")}
          />
          <TeaserCard
            to="/ai-studio"
            icon={Sparkles}
            className="bg-[radial-gradient(ellipse_at_90%_10%,rgb(167_139_250/0.4),transparent_60%)]"
            title={t("home.promo.aiTitle")}
            text={t("home.promo.aiText")}
            soon={t("home.promo.soon")}
          />
        </div>
      </section>

      <section className="container-page mt-20" aria-labelledby="featured-title">
        <SectionHeading
          index="02"
          id="featured-title"
          title={t("home.featuredTitle")}
          text={t("home.featuredText")}
          action={
            <Link to="/catalog" className="group inline-flex items-center gap-1.5 text-sm font-semibold text-primary">
              {t("home.viewAll")}
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" aria-hidden />
            </Link>
          }
        />
        <div className="mt-8">
          <ProductGrid products={featuredProducts} isLoading={featured.isLoading} skeletonCount={4} />
        </div>
      </section>
    </>
  );
}

function HeroStage() {
  const { t } = useTranslation();
  return (
    <div className="group relative mx-auto aspect-square w-full max-w-[420px] md:max-w-[600px]">
      <span
        aria-hidden
        className="heading-display text-outline pointer-events-none absolute top-1/2 left-0 hidden -translate-y-1/2 rotate-180 text-[clamp(40px,4.4vw,64px)] whitespace-nowrap [writing-mode:vertical-rl] md:block"
      >
        Your next look
      </span>
      <div
        aria-hidden
        className="absolute inset-[14%] rounded-full bg-[radial-gradient(circle,rgb(255_100_45/0.55),rgb(255_46_85/0.18)_45%,transparent_70%)] blur-2xl md:left-[20%]"
      />
      <figure className="relative z-10 mx-auto w-[80%] translate-y-[6%] md:w-[76%]">
        <div className="aspect-square overflow-hidden rounded-full shadow-[0_40px_60px_-20px_rgb(0_0_0/0.85)] ring-1 ring-white/15">
          <img
            src={heroPhoto}
            alt=""
            fetchPriority="high"
            className="size-full scale-[1.08] translate-x-[3%] -translate-y-[4%] object-cover"
          />
        </div>
        <figcaption className="mt-2 text-center text-[10px] text-muted-foreground">
          {t("product.photo", { credit: creditText("hero") })}
        </figcaption>
      </figure>
      <HudChip className="top-[10%] right-0">19″ · 8.5J · ET35</HudChip>
      <HudChip className="bottom-[22%] left-0 md:left-[10%]" tone="success">
        <Check className="size-3.5" aria-hidden /> {t("home.hud.fits")}
      </HudChip>
      <HudChip className="right-0 bottom-[14%]" tone="primary">
        {t("home.hud.price")}
      </HudChip>
    </div>
  );
}

function HudChip({
  className,
  tone = "default",
  children,
}: {
  className?: string;
  tone?: "default" | "success" | "primary";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "absolute z-20 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-xl backdrop-blur-md",
        tone === "default" && "border-white/15 bg-black/50 text-white",
        tone === "success" && "border-success/40 bg-success/15 text-success",
        tone === "primary" && "border-primary/50 bg-primary/20 text-[#ffc2a8]",
        className,
      )}
    >
      {children}
    </span>
  );
}

function SectionHeading({
  index,
  id,
  title,
  text,
  action,
}: {
  index: string;
  id: string;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="flex items-center gap-3 text-xs font-bold tracking-[0.2em] text-primary">
          {index}
          <span aria-hidden className="bg-brand-gradient h-px w-10" />
        </p>
        <h2 id={id} className="heading-display mt-3 text-4xl md:text-6xl">
          {title}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground md:text-base">{text}</p>
      </div>
      {action}
    </div>
  );
}

function TeaserCard({
  to,
  icon: Icon,
  className,
  title,
  text,
  soon,
}: {
  to: string;
  icon: LucideIcon;
  className: string;
  title: string;
  text: string;
  soon: string;
}) {
  return (
    <Link
      to={to}
      className={cn(
        "group relative flex flex-col justify-between gap-6 overflow-hidden rounded-3xl border border-white/[0.08] bg-card p-6 transition-all hover:-translate-y-1 hover:border-white/20",
        className,
      )}
    >
      <span className="flex items-center justify-between">
        <span className="grid size-11 place-items-center rounded-2xl bg-white/10">
          <Icon className="size-5" aria-hidden />
        </span>
        <span className="rounded-full border border-white/15 px-2.5 py-1 text-[10px] font-bold tracking-[0.15em] uppercase">
          {soon}
        </span>
      </span>
      <span>
        <b className="heading-display block text-3xl">{title}</b>
        <span className="mt-1 block text-sm text-muted-foreground">{text}</span>
      </span>
    </Link>
  );
}
