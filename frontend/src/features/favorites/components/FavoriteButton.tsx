import { Heart } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router";
import { toast } from "sonner";

import { useMe } from "@/features/auth";
import { cn } from "@/lib/utils";

import { useToggleFavorite } from "../hooks";

interface FavoriteButtonProps {
  productId: string;
  isFavorite: boolean;
  className?: string;
}

export function FavoriteButton({ productId, isFavorite, className }: FavoriteButtonProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: user } = useMe();
  const toggle = useToggleFavorite();
  const [optimistic, setOptimistic] = useState<boolean | null>(null);
  const active = optimistic ?? isFavorite;

  const onClick = () => {
    if (!user) {
      toast(t("favorites.loginRequired"));
      navigate(`/login?next=${encodeURIComponent(location.pathname + location.search)}`);
      return;
    }
    const next = !active;
    setOptimistic(next);
    toggle.mutate(
      { productId, favorite: next },
      {
        onError: () => toast.error(t("auth.genericError")),
        onSettled: () => setOptimistic(null),
      },
    );
  };

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={active ? t("favorites.remove") : t("favorites.add")}
      className={cn(
        "grid size-9 place-items-center rounded-full border border-border bg-background/80 backdrop-blur hover:bg-accent",
        className,
      )}
    >
      <Heart className={cn("size-4", active && "fill-primary text-primary")} aria-hidden />
    </button>
  );
}
