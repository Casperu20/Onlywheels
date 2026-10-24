import * as React from "react";

import { cn } from "@/lib/utils";

/** Styled native <select>: accessible and works well on mobile pickers. */
export function NativeSelect({ className, children, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "min-h-11 w-full min-w-0 rounded-md border border-input bg-[#15171b] px-3 py-2 text-sm text-foreground disabled:cursor-not-allowed disabled:opacity-45",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
