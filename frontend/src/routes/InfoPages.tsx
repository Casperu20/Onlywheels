import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { NotFoundPage } from "@/routes/ErrorPages";

const LEGAL_DOCS = ["terms", "privacy", "cookies"] as const;
type LegalDoc = (typeof LEGAL_DOCS)[number];

interface Section {
  title: string;
  text: string;
}

function PageTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="flex items-center gap-3 text-xs font-bold tracking-[0.2em] text-primary uppercase">
        {eyebrow}
        <span aria-hidden className="bg-brand-gradient h-px w-10" />
      </p>
      <h1 className="mt-3 text-5xl font-extrabold md:text-6xl">{title}</h1>
    </div>
  );
}

/** Placeholder legal texts – to be replaced with texts reviewed by a lawyer before launch. */
export function LegalPage() {
  const { t } = useTranslation();
  const { doc } = useParams();
  if (!LEGAL_DOCS.includes(doc as LegalDoc)) return <NotFoundPage />;

  const sections = t(`legal.${doc}.sections`, { returnObjects: true }) as Section[];

  return (
    <section className="container-page grid gap-10 py-12 lg:grid-cols-[1fr_260px]">
      <article className="flex max-w-3xl flex-col gap-8">
        <PageTitle eyebrow={t("footer.legal")} title={t(`legal.${doc}.title`)} />
        <p className="rounded-xl border border-amber/30 bg-amber/10 px-4 py-3 text-sm text-amber">{t("legal.draft")}</p>
        {sections.map((section) => (
          <div key={section.title}>
            <h2 className="text-lg font-bold">{section.title}</h2>
            <p className="mt-2 leading-relaxed text-muted-foreground">{section.text}</p>
          </div>
        ))}
        <p className="text-xs text-muted-foreground">{t("legal.updated")}</p>
      </article>
      <nav aria-label={t("footer.legal")} className="flex flex-col gap-2 self-start rounded-2xl border border-white/[0.08] bg-card p-5 lg:sticky lg:top-28">
        {LEGAL_DOCS.map((name) => (
          <Link
            key={name}
            to={`/legal/${name}`}
            aria-current={name === doc ? "page" : undefined}
            className="rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground aria-[current=page]:bg-primary/15 aria-[current=page]:text-foreground"
          >
            {t(`legal.${name}.title`)}
          </Link>
        ))}
        <Link to="/contact" className="rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground">
          {t("footer.contact")}
        </Link>
      </nav>
    </section>
  );
}

export function ContactPage() {
  const { t } = useTranslation();
  const items = [
    { icon: Mail, label: t("contact.email"), value: "contact@onlywheels.ro", href: "mailto:contact@onlywheels.ro" },
    { icon: Phone, label: t("contact.phone"), value: "+40 700 000 000", href: "tel:+40700000000" },
    { icon: MapPin, label: t("contact.address"), value: t("contact.addressValue") },
    { icon: Clock, label: t("contact.hours"), value: t("contact.hoursValue") },
  ];

  return (
    <section className="container-page flex flex-col gap-10 py-12">
      <PageTitle eyebrow={t("footer.help")} title={t("footer.contact")} />
      <p className="max-w-2xl text-muted-foreground">{t("contact.intro")}</p>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(({ icon: Icon, label, value, href }) => (
          <li key={label} className="flex flex-col gap-3 rounded-2xl border border-white/[0.08] bg-card p-5">
            <span className="grid size-11 place-items-center rounded-xl bg-primary/15 text-primary">
              <Icon className="size-5" aria-hidden />
            </span>
            <span className="text-xs font-bold tracking-[0.15em] text-muted-foreground uppercase">{label}</span>
            {href ? (
              <a href={href} className="font-semibold hover:text-primary">
                {value}
              </a>
            ) : (
              <span className="font-semibold">{value}</span>
            )}
          </li>
        ))}
      </ul>
      <div className="rounded-2xl border border-white/[0.08] bg-card p-6 text-sm text-muted-foreground">
        <p>{t("contact.company")}</p>
        <p className="mt-2">
          {t("contact.anpc")}{" "}
          <a href="https://anpc.ro/ce-este-sal/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
            ANPC – SAL
          </a>
        </p>
      </div>
    </section>
  );
}
