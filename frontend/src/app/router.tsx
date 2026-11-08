import type { ComponentType } from "react";
import { createBrowserRouter } from "react-router";

import { PageLoader } from "@/components/PageLoader";
import { RequireAuth } from "@/features/auth";
import { ErrorPage, NotFoundPage } from "@/routes/ErrorPages";
import { HomePage } from "@/routes/HomePage";

import { RootLayout } from "./layout/RootLayout";

/** Code splitting: each page module becomes its own chunk, loaded on first visit. */
function page<M>(load: () => Promise<M>, name: keyof M) {
  return async () => ({ Component: (await load())[name] as ComponentType });
}

const auth = () => import("@/routes/AuthPages");
const orders = () => import("@/routes/OrderPages");
const accountSub = () => import("@/routes/AccountSubPages");
const info = () => import("@/routes/InfoPages");

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <ErrorPage />,
    // Shown only while the first lazily loaded page of a visit is downloading.
    hydrateFallbackElement: <PageLoader />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "catalog", lazy: page(() => import("@/routes/CatalogPage"), "CatalogPage") },
      { path: "catalog/:slug", lazy: page(() => import("@/routes/ProductPage"), "ProductPage") },
      { path: "showroom", lazy: page(() => import("@/features/showroom3d/ShowroomPage"), "ShowroomPage") },
      { path: "fitting", lazy: page(orders, "FittingPage") },
      { path: "cart", lazy: page(() => import("@/routes/CartPage"), "CartPage") },
      { path: "login", lazy: page(auth, "LoginPage") },
      { path: "register", lazy: page(auth, "RegisterPage") },
      { path: "forgot-password", lazy: page(auth, "ForgotPasswordPage") },
      { path: "reset-password", lazy: page(auth, "ResetPasswordPage") },
      { path: "legal/:doc", lazy: page(info, "LegalPage") },
      { path: "contact", lazy: page(info, "ContactPage") },
      {
        element: <RequireAuth />,
        children: [
          { path: "checkout", lazy: page(() => import("@/routes/CheckoutPage"), "CheckoutPage") },
          { path: "checkout/success", lazy: page(orders, "CheckoutSuccessPage") },
          { path: "checkout/fake-pay", lazy: page(orders, "FakePayPage") },
          { path: "account", lazy: page(() => import("@/routes/AccountPage"), "AccountPage") },
          { path: "account/garage", lazy: page(accountSub, "GaragePage") },
          { path: "account/profile", lazy: page(accountSub, "ProfilePage") },
          { path: "account/favorites", lazy: page(accountSub, "FavoritesPage") },
          { path: "account/orders", lazy: page(orders, "OrdersPage") },
          { path: "account/orders/:number", lazy: page(orders, "OrderDetailPage") },
          { path: "ai-studio", lazy: page(() => import("@/routes/AIStudioPage"), "AIStudioPage") },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
