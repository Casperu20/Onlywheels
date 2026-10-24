import { zodResolver } from "@hookform/resolvers/zod";
import { useCallback, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { applyFieldErrors, getErrorMessage } from "@/api/errors";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/ui/button";

import { useGoogleLogin, useRegister } from "../hooks";
import { registerSchema } from "../schemas";
import { FormAlert } from "./AuthCard";
import { GoogleButton } from "./GoogleButton";
import { OrDivider } from "./LoginForm";

interface RegisterFormProps {
  onSuccess: () => void;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { t } = useTranslation();
  const registerUser = useRegister();
  const { mutateAsync: loginWithGoogle } = useGoogleLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: { first_name: "", last_name: "", email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerUser.mutateAsync({
        email: values.email,
        password: values.password,
        first_name: values.first_name,
        last_name: values.last_name,
      });
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
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label={t("auth.firstName")}
            autoComplete="given-name"
            error={errors.first_name?.message}
            {...register("first_name")}
          />
          <FormField
            label={t("auth.lastName")}
            autoComplete="family-name"
            error={errors.last_name?.message}
            {...register("last_name")}
          />
        </div>
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
          {t("auth.submitRegister")}
        </Button>
      </form>
      <OrDivider />
      <GoogleButton onCredential={onGoogleCredential} />
    </div>
  );
}
