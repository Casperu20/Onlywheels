import { Box, Grid3x3, House, ShoppingCart, Sparkles, Wrench, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  labelKey: string;
  icon: LucideIcon;
  tagKey?: string;
}

export const mainNav: NavItem[] = [
  { to: "/", labelKey: "nav.home", icon: House },
  { to: "/catalog", labelKey: "nav.catalog", icon: Grid3x3 },
  { to: "/showroom", labelKey: "nav.showroom", icon: Box, tagKey: "nav.explore" },
  { to: "/ai-studio", labelKey: "nav.aiStudio", icon: Sparkles },
  { to: "/fitting", labelKey: "nav.fitting", icon: Wrench },
];

export const mobileNav: NavItem[] = [
  { to: "/", labelKey: "nav.home", icon: House },
  { to: "/catalog", labelKey: "nav.catalog", icon: Grid3x3 },
  { to: "/showroom", labelKey: "nav.showroomShort", icon: Box },
  { to: "/ai-studio", labelKey: "nav.aiStudio", icon: Sparkles },
  { to: "/cart", labelKey: "nav.cart", icon: ShoppingCart },
];
