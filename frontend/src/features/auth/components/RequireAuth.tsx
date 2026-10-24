import { Navigate, Outlet, useLocation } from "react-router";

import { PageLoader } from "@/components/PageLoader";

import { useMe } from "../hooks";

/** Layout route: renders child routes only for logged-in users, otherwise redirects to /login. */
export function RequireAuth() {
  const { data: user, isPending } = useMe();
  const location = useLocation();

  if (isPending) return <PageLoader />;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet />;
}
