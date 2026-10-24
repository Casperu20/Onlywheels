import { Outlet, ScrollRestoration } from "react-router";

import { CartSync } from "@/features/cart";

import { AnnouncementBar } from "./AnnouncementBar";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";

export function RootLayout() {
  return (
    <>
      <AnnouncementBar />
      <Header />
      <main id="main">
        <Outlet />
      </main>
      <Footer />
      <MobileNav />
      <CartSync />
      <ScrollRestoration />
    </>
  );
}
