import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { toast } from "sonner";

import { PageLoader } from "@/components/PageLoader";
import {
  AuthCard,
  ForgotPasswordForm,
  LoginForm,
  RegisterForm,
  ResetPasswordForm,
  safeNextPath,
  useMe,
} from "@/features/auth";

function useRedirectAfterLogin() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const target = safeNextPath(params.get("next"));
  return { target, go: () => navigate(target, { replace: true }) };
}

export function LoginPage() {
  const { t } = useTranslation();
  const { data: user, isPending } = useMe();
  const { target, go } = useRedirectAfterLogin();

  if (isPending) return <PageLoader />;
  if (user) return <Navigate to={target} replace />;

  return (
    <AuthCard
      title={t("auth.loginTitle")}
      subtitle={t("auth.loginSubtitle")}
      footer={
        <>
          {t("auth.noAccount")}{" "}
          <Link to="/register" className="text-primary hover:underline">
            {t("auth.registerLink")}
          </Link>
        </>
      }
    >
      <LoginForm onSuccess={go} />
    </AuthCard>
  );
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { data: user, isPending } = useMe();
  const { target, go } = useRedirectAfterLogin();

  if (isPending) return <PageLoader />;
  if (user) return <Navigate to={target} replace />;

  return (
    <AuthCard
      title={t("auth.registerTitle")}
      subtitle={t("auth.registerSubtitle")}
      footer={
        <>
          {t("auth.haveAccount")}{" "}
          <Link to="/login" className="text-primary hover:underline">
            {t("auth.loginLink")}
          </Link>
        </>
      }
    >
      <RegisterForm onSuccess={go} />
    </AuthCard>
  );
}

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  return (
    <AuthCard
      title={t("auth.forgotTitle")}
      subtitle={t("auth.forgotSubtitle")}
      footer={
        <Link to="/login" className="text-primary hover:underline">
          {t("auth.backToLogin")}
        </Link>
      }
    >
      <ForgotPasswordForm />
    </AuthCard>
  );
}

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");

  return (
    <AuthCard title={t("auth.resetTitle")}>
      {uid && token ? (
        <ResetPasswordForm
          uid={uid}
          token={token}
          onSuccess={() => {
            toast.success(t("auth.resetDone"));
            navigate("/login", { replace: true });
          }}
        />
      ) : (
        <p role="alert" className="text-sm text-destructive">
          {t("auth.resetInvalidLink")}
        </p>
      )}
    </AuthCard>
  );
}
