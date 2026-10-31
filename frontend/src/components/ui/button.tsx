import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-bold transition-all active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-brand-gradient text-primary-foreground shadow-[0_10px_30px_-12px_rgb(255_100_45/0.9)] hover:brightness-110 hover:shadow-[0_14px_36px_-10px_rgb(255_70_60/0.9)]",
        secondary:
          "border border-white/15 bg-white/[0.03] text-secondary-foreground backdrop-blur hover:border-white/30 hover:bg-white/[0.07]",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
      },
      size: {
        default: "min-h-11 px-5 py-3",
        sm: "h-9 px-3",
        lg: "min-h-13 px-7 text-base",
        icon: "size-10 rounded-[10px] border border-white/10 hover:border-white/25",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

// eslint-disable-next-line react-refresh/only-export-components
export { buttonVariants };
