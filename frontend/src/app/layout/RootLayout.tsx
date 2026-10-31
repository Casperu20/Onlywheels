import { Outlet, ScrollRestoration } from "react-router";

import { CartSync } from "@/features/cart";

import { Footer } from "./Footer";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";

export function RootLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <MobileNav />
      <CartSync />
      <ScrollRestoration />
    </div>
  );
}
