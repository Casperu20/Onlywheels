import { Wrench } from "lucide-react";

import { cn } from "@/lib/utils";

import type { Finish, ProductType } from "../api";

const FINISH_COLORS: Record<Finish, string> = {
  silver: "#c9ccd1",
  black: "#2f3236",
  bronze: "#9a7046",
  gunmetal: "#5a5e66",
  chrome: "#e6e8eb",
  white: "#f2f2f2",
};

interface WheelVisualProps {
  type: ProductType;
  finish?: Finish | "";
  className?: string;
}

/** Placeholder artwork used until real product photos are uploaded in the admin. */
export function WheelVisual({ type, finish, className }: WheelVisualProps) {
  if (type === "accessory") {
    return (
      <div className={cn("grid aspect-square place-items-center", className)} aria-hidden>
        <Wrench className="size-1/3 text-muted-foreground" />
      </div>
    );
  }

  const rim = FINISH_COLORS[finish || "silver"];
  const showRim = type !== "tire";

  return (
    <svg viewBox="0 0 100 100" className={cn("aspect-square drop-shadow-xl", className)} aria-hidden>
      <circle cx="50" cy="50" r="48" fill="#141518" />
      <circle cx="50" cy="50" r="45" fill="none" stroke="#25272b" strokeWidth="3" strokeDasharray="2 2" />
      {showRim ? (
        <>
          <circle cx="50" cy="50" r="36" fill={rim} />
          <circle cx="50" cy="50" r="31" fill="#1c1d21" />
          {[0, 72, 144, 216, 288].map((angle) => (
            <rect
              key={angle}
              x="47"
              y="20"
              width="6"
              height="30"
              rx="3"
              fill={rim}
              transform={`rotate(${angle} 50 50)`}
            />
          ))}
          <circle cx="50" cy="50" r="9" fill={rim} />
          <circle cx="50" cy="50" r="3.5" fill="#1c1d21" />
        </>
      ) : (
        <>
          <circle cx="50" cy="50" r="30" fill="#2a2c30" />
          <circle cx="50" cy="50" r="24" fill="#c9ccd1" opacity="0.25" />
        </>
      )}
    </svg>
  );
}
