import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

import type { Badge } from "../api";

const TONES: Record<Badge, string> = {
  bestseller: "bg-amber/15 text-amber ring-amber/40",
  new: "bg-electric/15 text-electric ring-electric/40",
  our_pick: "bg-violet-400/15 text-violet-300 ring-violet-400/40",
  offer: "bg-hot/20 text-[#ff8aa0] ring-hot/50",
  summer: "bg-yellow-300/15 text-yellow-200 ring-yellow-300/40",
  winter: "bg-sky-300/15 text-sky-200 ring-sky-300/40",
  sport: "bg-primary/20 text-[#ffab85] ring-primary/50",
  set: "bg-success/15 text-success ring-success/40",
  accessory: "bg-white/10 text-zinc-300 ring-white/20",
};

export function ProductBadge({ badge, className }: { badge: Badge | ""; className?: string }) {
  const { t } = useTranslation();
  if (!badge) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[10px] leading-none font-extrabold tracking-[0.12em] uppercase ring-1 ring-inset backdrop-blur",
        TONES[badge] ?? TONES.accessory,
        className,
      )}
    >
      {t(`catalog.badges.${badge}`)}
    </span>
  );
}
