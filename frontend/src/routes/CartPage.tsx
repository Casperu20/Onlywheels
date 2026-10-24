import { ArrowRight, Minus, Plus, ShoppingCart, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { PageLoader } from "@/components/PageLoader";
import { Button } from "@/components/ui/button";
import { MAX_QUANTITY, useCart, useCartActions, type CartLine } from "@/features/cart";
import { WheelVisual, variantSummary } from "@/features/catalog";
import { formatPrice } from "@/lib/format";
import { useLocale } from "@/lib/useLocale";

export function CartPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const cart = useCart();

  if (cart.isLoading) return <PageLoader />;

  return (
    <section className="container-page flex flex-col gap-8 py-10" aria-labelledby="cart-title">
      <h1 id="cart-title" className="text-3xl font-extrabold tracking-tight">
        {t("pages.cart.title")}
      </h1>

      {cart.lines.length === 0 ? (
        <div className="grid place-items-center gap-4 rounded-2xl border border-dashed border-border py-16 text-center">
          <ShoppingCart className="size-8 text-muted-foreground" aria-hidden />
          <p className="font-semibold">{t("cart.empty")}</p>
          <Button asChild>
            <Link to="/catalog">{t("home.ctaCatalog")}</Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
          <ul className="flex flex-col gap-3">
            {cart.lines.map((line) => (
              <CartLineRow key={line.key} line={line} />
            ))}
          </ul>
          <aside className="flex h-fit flex-col gap-4 rounded-2xl border border-border bg-card p-6">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("checkout.subtotal")}</span>
              <span className="font-bold">{formatPrice(cart.subtotal, locale)}</span>
            </div>
            <p className="text-xs text-muted-foreground">{t("cart.shippingHint")}</p>
            <Button asChild size="lg">
              <Link to="/checkout">
                {t("cart.checkout")} <ArrowRight aria-hidden />
              </Link>
            </Button>
            {cart.isGuest && <p className="text-xs text-muted-foreground">{t("cart.loginHint")}</p>}
          </aside>
        </div>
      )}
    </section>
  );
}

function CartLineRow({ line }: { line: CartLine }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const { setQuantity, remove } = useCartActions();
  const busy = setQuantity.isPending || remove.isPending;

  return (
    <li className="flex flex-wrap items-center gap-4 rounded-2xl border border-border p-4">
      <WheelVisual type={line.product.type} finish={line.variant.finish} className="w-16 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-bold tracking-[1.5px] text-muted-foreground uppercase">{line.product.brand}</p>
        <Link to={`/catalog/${line.product.slug}`} className="font-semibold hover:underline">
          {line.product.name}
        </Link>
        <p className="text-xs text-muted-foreground">{variantSummary(line.variant, line.product.type)}</p>
        {line.available < line.quantity && (
          <p className="text-xs text-destructive">{t("cart.lowStock", { count: line.available })}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="icon"
          aria-label={t("product.decrease")}
          disabled={busy || line.quantity <= 1}
          onClick={() => setQuantity.mutate({ line, quantity: line.quantity - 1 })}
        >
          <Minus aria-hidden />
        </Button>
        <span className="w-8 text-center font-bold">{line.quantity}</span>
        <Button
          variant="secondary"
          size="icon"
          aria-label={t("product.increase")}
          disabled={busy || line.quantity >= MAX_QUANTITY}
          onClick={() => setQuantity.mutate({ line, quantity: line.quantity + 1 })}
        >
          <Plus aria-hidden />
        </Button>
      </div>
      <p className="w-28 text-right font-bold">{formatPrice(line.lineTotal, locale)}</p>
      <Button variant="ghost" size="icon" aria-label={t("cart.remove")} disabled={busy} onClick={() => remove.mutate(line)}>
        <Trash2 aria-hidden />
      </Button>
    </li>
  );
}
