import { zodResolver } from "@hookform/resolvers/zod";
import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { applyFieldErrors, getErrorMessage } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";

import { useGoogleLogin, useLogin } from "../hooks";
import { loginSchema } from "../schemas";
import { FormAlert } from "./AuthCard";
import { GoogleButton } from "./GoogleButton";

interface LoginFormProps {
  onSuccess: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { t } = useTranslation();
  const login = useLogin();
  const { mutateAsync: loginWithGoogle } = useGoogleLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login.mutateAsync(values);
      onSuccess();
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        setFormError(getErrorMessage(error, t("auth.genericError")));
      }
    }
  });

  const onGoogleCredential = useCallback(
    async (credential: string) => {
      setFormError(null);
      try {
        await loginWithGoogle(credential);
        onSuccess();
      } catch (error) {
        setFormError(getErrorMessage(error, t("auth.googleError")));
      }
    },
    [loginWithGoogle, onSuccess, t],
  );

  return (
    <div className="flex flex-col gap-5">
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        <FormAlert message={formError} />
        <FormField
          label={t("auth.email")}
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          label={t("auth.password")}
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Link to="/forgot-password" className="self-end text-xs text-primary hover:underline">
          {t("auth.forgotPassword")}
        </Link>
        <Button type="submit" disabled={isSubmitting}>
          {t("auth.submitLogin")}
        </Button>
      </form>
      <OrDivider />
      <GoogleButton onCredential={onGoogleCredential} />
    </div>
  );
}

export function OrDivider() {
  const { t } = useTranslation();
  if (!import.meta.env.VITE_GOOGLE_CLIENT_ID) return null;
  return (
    <div className="flex items-center gap-3 text-xs text-muted-foreground">
      <span className="h-px flex-1 bg-border" />
      {t("auth.or")}
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
