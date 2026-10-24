import { Link } from "react-router";

import { cn } from "@/lib/utils";

export function Logo({ small = false }: { small?: boolean }) {
  const size = small ? 28 : 37;
  return (
    <Link
      to="/"
      aria-label="OnlyWheels"
      className={cn(
        "flex items-center gap-2 font-extrabold tracking-[-1.2px] whitespace-nowrap",
        small ? "text-lg" : "text-[23px]",
      )}
    >
      <img src="/onlywheels-logo.svg" alt="" width={size} height={size} />
      Only<span className="text-primary">Wheels</span>
    </Link>
  );
}
