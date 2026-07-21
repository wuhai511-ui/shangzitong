import { NavLink, Outlet } from "react-router-dom";
import { House, WalletCards, Route, Bell, UserRound } from "lucide-react";
import { BrandMark } from "../components/BrandMark";

const navItems = [
  { to: "/", label: "首页", icon: House },
  { to: "/funds", label: "资金", icon: WalletCards },
  { to: "/planning", label: "规划", icon: Route },
  { to: "/alerts", label: "提醒", icon: Bell },
  { to: "/me", label: "我的", icon: UserRound },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <BrandMark className="app-brand-desktop" />
      <nav className="app-nav" aria-label="主导航">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"} className="nav-link">
            <Icon size={22} aria-hidden />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
