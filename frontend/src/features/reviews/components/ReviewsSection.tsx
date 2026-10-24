import { BadgeCheck, Star } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router";

import { getErrorMessage } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useMe } from "@/features/auth";
import { useLocale } from "@/lib/useLocale";
import { cn } from "@/lib/utils";

import { useCreateReview, useMyReview, useReviews } from "../api";

export function Stars({ value, className }: { value: number; className?: string }) {
  return (
    <span className={cn("inline-flex", className)} aria-label={`${value} / 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={cn("size-4", n <= Math.round(value) ? "fill-primary text-primary" : "text-muted-foreground")}
          aria-hidden
        />
      ))}
    </span>
  );
}

interface ReviewsSectionProps {
  productId: string;
  productSlug: string;
  ratingAvg: string;
  ratingCount: number;
}

export function ReviewsSection({ productId, productSlug, ratingAvg, ratingCount }: ReviewsSectionProps) {
  const { t } = useTranslation();
  const locale = useLocale();
  const location = useLocation();
  const { data: user } = useMe();
  const reviews = useReviews(productSlug);
  const mine = useMyReview(productSlug, Boolean(user));

  return (
    <section className="mt-16 flex flex-col gap-6" aria-labelledby="reviews-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="reviews-title" className="text-2xl font-extrabold tracking-tight">
          {t("reviews.title")}
        </h2>
        {ratingCount > 0 && (
          <p className="flex items-center gap-2 text-sm">
            <Stars value={Number(ratingAvg)} /> {Number(ratingAvg).toFixed(1)} · {t("reviews.count", { count: ratingCount })}
          </p>
        )}
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
        <ul className="flex flex-col gap-4">
          {reviews.data?.results.length ? (
            reviews.data.results.map((review) => (
              <li key={review.id} className="rounded-2xl border border-border p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <Stars value={review.rating} />
                  {review.title && <span className="font-semibold">{review.title}</span>}
                </div>
                {review.body && <p className="mt-2 text-sm text-muted-foreground">{review.body}</p>}
                <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                  {review.author} · {new Date(review.created_at).toLocaleDateString(locale)}
                  {review.is_verified_purchase && (
                    <span className="inline-flex items-center gap-1 text-success">
                      <BadgeCheck className="size-3.5" aria-hidden /> {t("reviews.verified")}
                    </span>
                  )}
                </p>
              </li>
            ))
          ) : (
            <li className="text-sm text-muted-foreground">{t("reviews.none")}</li>
          )}
        </ul>

        <div className="h-fit rounded-2xl border border-border bg-card p-5">
          {!user ? (
            <p className="text-sm text-muted-foreground">
              <Link to={`/login?next=${encodeURIComponent(location.pathname)}`} className="text-primary hover:underline">
                {t("auth.loginLink")}
              </Link>{" "}
              {t("reviews.loginToWrite")}
            </p>
          ) : mine.data ? (
            <p className="text-sm text-muted-foreground">
              {mine.data.status === "pending" ? t("reviews.pending") : t("reviews.alreadyReviewed")}
            </p>
          ) : (
            <ReviewForm productId={productId} productSlug={productSlug} />
          )}
        </div>
      </div>
    </section>
  );
}

function ReviewForm({ productId, productSlug }: { productId: string; productSlug: string }) {
  const { t } = useTranslation();
  const create = useCreateReview(productSlug);
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (rating < 1) {
      setError(t("reviews.chooseRating"));
      return;
    }
    setError(null);
    create.mutate(
      { product_id: productId, rating, title, body },
      { onError: (e) => setError(getErrorMessage(e, t("auth.genericError"))) },
    );
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <h3 className="font-semibold">{t("reviews.write")}</h3>
      <div role="radiogroup" aria-label={t("reviews.rating")} className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={rating === n}
            aria-label={`${n} / 5`}
            onClick={() => setRating(n)}
          >
            <Star className={cn("size-6", n <= rating ? "fill-primary text-primary" : "text-muted-foreground")} aria-hidden />
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="review-title">{t("reviews.reviewTitle")}</Label>
        <Input id="review-title" maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="review-body">{t("reviews.body")}</Label>
        <textarea
          id="review-body"
          rows={4}
          maxLength={2000}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="rounded-md border border-input bg-[#15171b] px-3 py-2 text-sm"
        />
      </div>
      {error && (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={create.isPending}>
        {t("reviews.submit")}
      </Button>
      <p className="text-xs text-muted-foreground">{t("reviews.moderationHint")}</p>
    </form>
  );
}
