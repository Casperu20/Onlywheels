import { createBrowserRouter } from "react-router";

import { RequireAuth } from "@/features/auth";
import { AccountPage } from "@/routes/AccountPage";
import { FavoritesPage, GaragePage } from "@/routes/AccountSubPages";
import { ForgotPasswordPage, LoginPage, RegisterPage, ResetPasswordPage } from "@/routes/AuthPages";
import { CartPage } from "@/routes/CartPage";
import { CatalogPage } from "@/routes/CatalogPage";
import { CheckoutPage } from "@/routes/CheckoutPage";
import { ErrorPage, NotFoundPage } from "@/routes/ErrorPages";
import { HomePage } from "@/routes/HomePage";
import {
  CheckoutSuccessPage,
  FakePayPage,
  FittingPage,
  OrderDetailPage,
  OrdersPage,
} from "@/routes/OrderPages";
import { PlaceholderPage } from "@/routes/PlaceholderPage";
import { ProductPage } from "@/routes/ProductPage";

import { RootLayout } from "./layout/RootLayout";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "catalog", element: <CatalogPage /> },
      { path: "catalog/:slug", element: <ProductPage /> },
      { path: "showroom", element: <PlaceholderPage page="showroom" /> },
      { path: "ai-studio", element: <PlaceholderPage page="aiStudio" /> },
      { path: "fitting", element: <FittingPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "forgot-password", element: <ForgotPasswordPage /> },
      { path: "reset-password", element: <ResetPasswordPage /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "checkout", element: <CheckoutPage /> },
          { path: "checkout/success", element: <CheckoutSuccessPage /> },
          { path: "checkout/fake-pay", element: <FakePayPage /> },
          { path: "account", element: <AccountPage /> },
          { path: "account/garage", element: <GaragePage /> },
          { path: "account/favorites", element: <FavoritesPage /> },
          { path: "account/orders", element: <OrdersPage /> },
          { path: "account/orders/:number", element: <OrderDetailPage /> },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
