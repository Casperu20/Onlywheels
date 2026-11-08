import { Link } from "react-router";

import { cn } from "@/lib/utils";

interface LogoProps {
  small?: boolean;
  markOnly?: boolean;
  className?: string;
}

export function Logo({ small = false, markOnly = false, className }: LogoProps) {
  return (
    <Link
      to="/"
      aria-label="OnlyWheels"
      className={cn(
        "group flex shrink-0 items-center transition-transform focus-visible:outline-none",
        className,
      )}
    >
      <picture>
        <source
          srcSet={markOnly ? "/onlywheels-mark.webp" : "/onlywheels-logo.webp"}
          type="image/webp"
        />
        <img
          src={markOnly ? "/onlywheels-mark.png" : "/onlywheels-logo.png"}
          alt="OnlyWheels"
          className={cn(
            "w-auto object-contain transition-transform duration-300 group-hover:scale-105 group-active:scale-95",
            markOnly
              ? small
                ? "size-8"
                : "size-10 sm:size-11"
              : small
                ? "h-7 sm:h-8"
                : "h-9 sm:h-11 md:h-12",
          )}
        />
      </picture>
    </Link>
  );
}
