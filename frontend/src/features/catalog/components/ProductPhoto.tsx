import { cn } from "@/lib/utils";

import type { Finish, ProductType, WheelStyle } from "../api";
import { WheelVisual } from "./WheelVisual";

export interface ProductPhotoProps {
  src?: string | null;
  alt?: string;
  className?: string;
  eager?: boolean;
  type?: ProductType;
  finish?: Finish | "";
  style?: WheelStyle | "";
  spin?: boolean;
  slug?: string;
}

export function ProductPhoto({
  src,
  alt = "",
  className,
  eager = false,
  type = "wheel",
  finish,
  style,
  spin = false,
  slug,
}: ProductPhotoProps) {
  if (!src) {
    return (
      <div className={cn("relative grid place-items-center bg-studio size-full overflow-hidden", className)}>
        <WheelVisual
          type={type}
          finish={finish}
          style={style}
          spin={spin}
          slug={slug}
          className="size-[85%]"
        />
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
