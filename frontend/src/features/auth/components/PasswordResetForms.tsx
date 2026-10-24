import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { getApiError, getErrorMessage } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";

import { useConfirmPasswordReset, useRequestPasswordReset } from "../hooks";
import { forgotPasswordSchema, resetPasswordSchema } from "../schemas";
import { FormAlert } from "./AuthCard";

export function ForgotPasswordForm() {
  const { t } = useTranslation();
  const requestReset = useRequestPasswordReset();
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(forgotPasswordSchema), defaultValues: { email: "" } });

  const onSubmit = handleSubmit(async ({ email }) => {
    setFormError(null);
    try {
      await requestReset.mutateAsync(email);
      setSent(true);
    } catch (error) {
      setFormError(getErrorMessage(error, t("auth.genericError")));
    }
  });

  if (sent) {
    return (
      <p role="status" className="rounded-md bg-success/10 px-3 py-2 text-sm text-success">
        {t("auth.forgotSent")}
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      <FormAlert message={formError} />
      <FormField
        label={t("auth.email")}
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register("email")}
      />
      <Button type="submit" disabled={isSubmitting}>
        {t("auth.forgotSubmit")}
      </Button>
    </form>
  );
}

interface ResetPasswordFormProps {
  uid: string;
  token: string;
  onSuccess: () => void;
}

export function ResetPasswordForm({ uid, token, onSuccess }: ResetPasswordFormProps) {
  const { t } = useTranslation();
  const confirmReset = useConfirmPasswordReset();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  const onSubmit = handleSubmit(async ({ password }) => {
    setFormError(null);
    try {
      await confirmReset.mutateAsync({ uid, token, new_password: password });
      onSuccess();
    } catch (error) {
      const passwordErrors = getApiError(error)?.fields?.new_password;
      if (passwordErrors?.length) {
        setError("password", { type: "server", message: passwordErrors[0] });
      } else {
        setFormError(t("auth.resetInvalidLink"));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      <FormAlert message={formError} />
      <FormField
        label={t("auth.newPassword")}
        type="password"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register("password")}
      />
      <FormField
        label={t("auth.confirmPassword")}
        type="password"
        autoComplete="new-password"
        error={errors.confirmPassword?.message}
        {...register("confirmPassword")}
      />
      <Button type="submit" disabled={isSubmitting}>
        {t("auth.resetSubmit")}
      </Button>
    </form>
  );
}
