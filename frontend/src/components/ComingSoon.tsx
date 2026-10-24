import { ArrowLeft, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";

interface ComingSoonProps {
  eyebrow: string;
  title: string;
  description: string;
}

export function ComingSoon({ eyebrow, title, description }: ComingSoonProps) {
  const { t } = useTranslation();

  return (
    <section className="container-page py-16 md:py-24">
      <div className="mx-auto max-w-2xl rounded-2xl border border-border bg-linear-to-br from-[#222429] to-card p-8 text-center md:p-12">
        <p className="mb-4 text-[10px] font-bold uppercase tracking-[2px] text-primary">{eyebrow}</p>
        <h1 className="mb-4 text-3xl font-extrabold tracking-tight md:text-5xl">{title}</h1>
        <p className="mb-8 text-muted-foreground">{description}</p>
        <span className="mb-8 inline-flex items-center gap-2 rounded-full bg-[#35251e] px-3 py-1 text-xs font-bold text-[#ff9a70]">
          <Sparkles aria-hidden /> {t("comingSoon.badge")}
        </span>
        <div>
          <Button asChild variant="secondary">
            <Link to="/">
              <ArrowLeft aria-hidden /> {t("comingSoon.back")}
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
