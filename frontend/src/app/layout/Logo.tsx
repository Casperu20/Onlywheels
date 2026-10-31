import { Link } from "react-router";

import { cn } from "@/lib/utils";

export function Logo({ small = false }: { small?: boolean }) {
  return (
    <Link
      to="/"
      aria-label="OnlyWheels"
      className={cn(
        "group flex shrink-0 items-center gap-2 font-display font-extrabold tracking-tight whitespace-nowrap uppercase italic",
        small ? "text-xl" : "text-[22px] sm:text-[27px]",
      )}
    >
      <img
        src="/onlywheels-logo.svg"
        alt=""
        className={cn("shrink-0", small ? "size-8" : "size-9 sm:size-11")}
      />
      <span>
        Only<span className="text-gradient pr-0.5">Wheels</span>
      </span>
    </Link>
  );
}
