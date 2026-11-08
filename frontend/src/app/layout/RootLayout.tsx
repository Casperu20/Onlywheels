import { Outlet, ScrollRestoration } from "react-router";

import { CartSync } from "@/features/cart";

import { Footer } from "./Footer";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";

export function RootLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className="relative z-0 flex-1 pb-20 lg:pb-0">
        <Outlet />
      </main>
      <Footer />
      <MobileNav />
      <CartSync />
      <ScrollRestoration />
    </div>
  );
}
