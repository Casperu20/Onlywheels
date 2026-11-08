import { Download, ImagePlus, Loader2, RotateCcw, Sparkles, Trash2, X } from "lucide-react";
import { useEffect, useId, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { toast } from "sonner";

import { getApiError, getErrorMessage } from "@/api/errors";
import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  isActive,
  useCreateGeneration,
  useDeleteGeneration,
  useGenerations,
  usePrivateImage,
  useRetryGeneration,
  useStudioInfo,
  type Generation,
  type StudioInfo,
} from "@/features/ai-studio";
import { cn } from "@/lib/utils";

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];

export function AIStudioPage() {
  const { t } = useTranslation();
  const info = useStudioInfo();
  const generations = useGenerations();

  if (info.isPending) return <PageLoader />;

  return (
    <section className="container-page py-10">
      <header className="mb-8 max-w-2xl">
        <p className="text-[10px] font-bold tracking-[2px] text-primary uppercase">{t("pages.aiStudio.eyebrow")}</p>
        <h1 className="heading-display mt-2 text-4xl md:text-5xl">{t("pages.aiStudio.title")}</h1>
        <p className="mt-3 text-muted-foreground">{t("pages.aiStudio.description")}</p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr]">
        {info.data?.enabled ? (
          <StudioForm info={info.data} />
        ) : (
          <div role="status" className="h-fit rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            <p className="font-semibold text-foreground">{t("aiStudio.unavailableTitle")}</p>
            <p className="mt-2">{t("aiStudio.unavailable")}</p>
          </div>
        )}

        <div>
          <h2 className="mb-4 text-lg font-bold">{t("aiStudio.history")}</h2>
          {generations.isError && <p className="text-sm text-destructive">{t("aiStudio.loadError")}</p>}
          {generations.data?.length === 0 && <p className="text-sm text-muted-foreground">{t("aiStudio.empty")}</p>}
          <ul className="grid gap-4 sm:grid-cols-2">
            {generations.data?.map((generation) => (
              <GenerationCard key={generation.id} generation={generation} />
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function StudioForm({ info }: { info: StudioInfo }) {
  const { t } = useTranslation();
  const ids = { photo: useId(), scene: useId(), style: useId(), error: useId() };
  const [searchParams, setSearchParams] = useSearchParams();
  const variant = searchParams.get("variant");
  const wheelName = searchParams.get("wheel");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [scene, setScene] = useState(info.scenes[0]?.value ?? "");
  const [style, setStyle] = useState(info.styles[0]?.value ?? "");
  const [error, setError] = useState<string | null>(null);
  const create = useCreateGeneration();
  const noneLeft = info.remaining_today <= 0;

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const pickFile = (picked: File | undefined) => {
    setError(null);
    if (!picked) return setFile(null);
    if (!ACCEPTED.includes(picked.type)) {
      setFile(null);
      return setError(t("aiStudio.wrongType"));
    }
    if (picked.size > info.max_upload_bytes) {
      setFile(null);
      return setError(t("aiStudio.tooLarge", { mb: Math.round(info.max_upload_bytes / 1024 / 1024) }));
    }
    setFile(picked);
  };

  const clearWheel = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("variant");
    next.delete("wheel");
    setSearchParams(next, { replace: true });
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!file) return setError(t("aiStudio.choosePhoto"));
    setError(null);
    create.mutate(
      { image: file, scene, style, variant },
      {
        onSuccess: () => {
          setFile(null);
          toast.success(t("aiStudio.queued"));
        },
        onError: (err) => {
          const fields = getApiError(err)?.fields;
          const fieldMessage = fields && Object.values(fields).flat()[0];
          setError(typeof fieldMessage === "string" ? fieldMessage : getErrorMessage(err, t("auth.genericError")));
        },
      },
    );
  };

  return (
    <form onSubmit={onSubmit} className="flex h-fit flex-col gap-5 rounded-2xl border border-border bg-card p-6" noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor={ids.photo}>{t("aiStudio.photo")}</Label>
        <label
          htmlFor={ids.photo}
          className="flex aspect-video cursor-pointer items-center justify-center overflow-hidden rounded-xl border border-dashed border-white/20 bg-[#15171b] text-sm text-muted-foreground hover:border-white/40"
        >
          {preview ? (
            <img src={preview} alt={t("aiStudio.preview")} className="size-full object-cover" />
          ) : (
            <span className="flex flex-col items-center gap-2 p-4 text-center">
              <ImagePlus className="size-6" aria-hidden />
              {t("aiStudio.photoHint")}
            </span>
          )}
        </label>
        <input
          id={ids.photo}
          type="file"
          accept={ACCEPTED.join(",")}
          className="sr-only"
          aria-describedby={error ? ids.error : undefined}
          onChange={(event) => pickFile(event.target.files?.[0])}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">{t("aiStudio.wheels")}</span>
        {variant ? (
          <p className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm">
            <span>{wheelName || t("aiStudio.selectedWheel")}</span>
            <button type="button" onClick={clearWheel} aria-label={t("aiStudio.clearWheel")} className="text-muted-foreground hover:text-foreground">
              <X className="size-4" aria-hidden />
            </button>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            {t("aiStudio.anyWheels")}{" "}
            <Link to="/catalog?type=wheel" className="text-primary hover:underline">
              {t("aiStudio.pickWheels")}
            </Link>
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={ids.scene}>{t("aiStudio.scene")}</Label>
          <NativeSelect id={ids.scene} value={scene} onChange={(e) => setScene(e.target.value)}>
            {info.scenes.map((option) => (
              <option key={option.value} value={option.value}>
                {t(`aiStudio.scenes.${option.value}`, { defaultValue: option.label })}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor={ids.style}>{t("aiStudio.style")}</Label>
          <NativeSelect id={ids.style} value={style} onChange={(e) => setStyle(e.target.value)}>
            {info.styles.map((option) => (
              <option key={option.value} value={option.value}>
                {t(`aiStudio.styles.${option.value}`, { defaultValue: option.label })}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>

      {error && (
        <p id={ids.error} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <p className="text-sm text-muted-foreground" aria-live="polite">
        {noneLeft
          ? t("aiStudio.quotaUsed")
          : t("aiStudio.quota", { remaining: info.remaining_today, limit: info.daily_limit })}
      </p>
      <Button type="submit" size="lg" disabled={create.isPending || noneLeft}>
        {create.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Sparkles aria-hidden />}
        {t("aiStudio.generate")}
      </Button>
      <p className="text-xs text-muted-foreground">{t("aiStudio.privacy", { days: info.retention_days })}</p>
    </form>
  );
}

function GenerationCard({ generation }: { generation: Generation }) {
  const { t } = useTranslation();
  const input = usePrivateImage(generation.input_url);
  const result = usePrivateImage(generation.result_url);
  const remove = useDeleteGeneration();
  const retry = useRetryGeneration();
  const active = isActive(generation.status);

  const onRetry = () =>
    retry.mutate(generation.id, {
      onSuccess: () => toast.success(t("aiStudio.queued")),
      onError: (err) => toast.error(getErrorMessage(err, t("auth.genericError"))),
    });
  const onDelete = () =>
    remove.mutate(generation.id, {
      onError: (err) => toast.error(getErrorMessage(err, t("auth.genericError"))),
    });

  return (
    <li className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card">
      <figure className="relative aspect-video bg-[#15171b]">
        {result.src ? (
          <img src={result.src} alt={t("aiStudio.resultAlt")} className="size-full object-cover" />
        ) : input.src ? (
          <img src={input.src} alt={t("aiStudio.inputAlt")} className={cn("size-full object-cover", active && "opacity-50")} />
        ) : null}
        {active && (
          <span className="absolute inset-0 flex items-center justify-center gap-2 text-sm font-semibold">
            <Loader2 className="size-4 animate-spin" aria-hidden /> {t(`aiStudio.status.${generation.status}`)}
          </span>
        )}
        {result.src && (
          <figcaption className="absolute bottom-2 left-2 rounded-full bg-black/70 px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase">
            {t("aiStudio.illustrative")}
          </figcaption>
        )}
      </figure>
      <div className="flex flex-1 flex-col gap-2 p-4 text-sm">
        <p className="font-semibold">
          {t(`aiStudio.scenes.${generation.scene}`, { defaultValue: generation.scene })}
          {" · "}
          {t(`aiStudio.styles.${generation.style}`, { defaultValue: generation.style })}
        </p>
        {generation.variant_name && <p className="text-muted-foreground">{generation.variant_name}</p>}
        {!active && <p className="text-xs text-muted-foreground">{t(`aiStudio.status.${generation.status}`)}</p>}
        {generation.status === "failed" && generation.error && (
          <p role="alert" className="text-destructive">
            {generation.error}
          </p>
        )}
        <div className="mt-auto flex flex-wrap gap-2 pt-2">
          {result.src && (
            <Button asChild size="sm" variant="secondary">
              <a href={result.src} download={`onlywheels-ai-${generation.id.slice(0, 8)}`}>
                <Download aria-hidden /> {t("aiStudio.download")}
              </a>
            </Button>
          )}
          {generation.status === "failed" && generation.input_url && (
            <Button size="sm" variant="secondary" disabled={retry.isPending} onClick={onRetry}>
              <RotateCcw aria-hidden /> {t("aiStudio.retry")}
            </Button>
          )}
          <Button size="sm" variant="ghost" disabled={remove.isPending} onClick={onDelete}>
            <Trash2 aria-hidden /> {t("aiStudio.delete")}
          </Button>
        </div>
      </div>
    </li>
  );
}
