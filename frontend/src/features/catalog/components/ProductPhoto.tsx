import { ImageOff } from "lucide-react";

import { cn } from "@/lib/utils";

export function ProductPhoto({
  src,
  alt = "",
  className,
  eager = false,
}: {
  src?: string | null;
  alt?: string;
  className?: string;
  eager?: boolean;
}) {
  if (!src) {
    return (
      <div className={cn("grid place-items-center bg-muted text-muted-foreground", className)}>
        <ImageOff className="size-1/4 max-w-10" aria-hidden />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      className={cn("object-cover", className)}
    />
  );
}
