import { Download, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { getApiError } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";

import { authApi, type User } from "../api";
import { useDeleteAccount } from "../hooks";

/** GDPR: download personal data and delete the account. */
export function PrivacySection({ user }: { user: User }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const deleteAccount = useDeleteAccount();
  const [exporting, setExporting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string>();

  const download = async () => {
    setExporting(true);
    try {
      const data = await authApi.exportData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = Object.assign(document.createElement("a"), { href: url, download: "onlywheels-data.json" });
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      toast.error(t("auth.genericError"));
    } finally {
      setExporting(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError(undefined);
    const payload = user.has_password ? { password: value } : { confirm_email: value };
    deleteAccount.mutate(payload, {
      onSuccess: () => {
        toast.success(t("privacy.deleted"));
        navigate("/", { replace: true });
      },
      onError: (err) =>
        setError(getApiError(err)?.fields ? t("privacy.deleteWrong") : t("auth.genericError")),
    });
  };

  return (
    <section aria-labelledby="privacy-title" className="mt-10 max-w-xl rounded-2xl border border-border p-6">
      <h2 id="privacy-title" className="text-lg font-bold">
        {t("privacy.title")}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{t("privacy.text")}</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button variant="secondary" disabled={exporting} onClick={download}>
          <Download aria-hidden /> {t("privacy.export")}
        </Button>
        {!confirming && (
          <Button variant="destructive" onClick={() => setConfirming(true)}>
            <Trash2 aria-hidden /> {t("privacy.delete")}
          </Button>
        )}
      </div>
      {confirming && (
        <form onSubmit={submit} noValidate className="mt-5 flex flex-col gap-4">
          <p className="text-sm text-destructive">{t("privacy.deleteWarning")}</p>
          <FormField
            label={user.has_password ? t("auth.password") : t("privacy.typeEmail")}
            type={user.has_password ? "password" : "email"}
            autoComplete={user.has_password ? "current-password" : "off"}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            error={error}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" variant="destructive" disabled={!value || deleteAccount.isPending}>
              {t("privacy.deleteConfirm")}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setConfirming(false)}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
