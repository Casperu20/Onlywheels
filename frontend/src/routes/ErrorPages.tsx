import { useTranslation } from "react-i18next";
import { Link, isRouteErrorResponse, useRouteError } from "react-router";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <section className="container-page py-24 text-center">
      <p className="text-6xl font-black text-primary">404</p>
      <h1 className="mt-4 text-2xl font-extrabold">{t("notFound.title")}</h1>
      <p className="mt-2 text-muted-foreground">{t("notFound.text")}</p>
      <Button asChild className="mt-8">
        <Link to="/">{t("notFound.back")}</Link>
      </Button>
    </section>
  );
}

export function ErrorPage() {
  const { t } = useTranslation();
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFoundPage />;

  return (
    <section className="container-page py-24 text-center">
      <h1 className="text-2xl font-extrabold">{t("error.title")}</h1>
      <p className="mt-2 text-muted-foreground">{t("error.text")}</p>
      <Button className="mt-8" onClick={() => window.location.reload()}>
        {t("error.retry")}
      </Button>
    </section>
  );
}
