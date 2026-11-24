import clsx from "clsx";
import { Database, Languages, LayoutDashboard, Menu, Moon, ScanSearch, Sun, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { useTheme } from "../lib/theme";
import { Logo } from "./Logo";

// Only pages that are implemented and connected to real data appear here.
const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/inspector", label: "Unicode Inspector", icon: ScanSearch, end: false },
  { to: "/multilingual", label: "Multilingual Lab", icon: Languages, end: false },
  { to: "/datasets", label: "Dataset Explorer", icon: Database, end: false },
] as const;

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="flex flex-col gap-0.5">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                isActive
                  ? "bg-violet-500/10 text-fg ring-1 ring-violet-500/25"
                  : "text-muted hover:bg-surface-2 hover:text-fg",
              )
            }
          >
            <Icon className="size-4" aria-hidden="true" />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2 px-2.5">
      <Logo />
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight">EmojiLens</div>
        <div className="text-[11px] text-muted">Security research console</div>
      </div>
    </div>
  );
}

export function AppShell() {
  const { theme, toggle } = useTheme();
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const current = NAV.find((n) =>
    n.end ? location.pathname === n.to : location.pathname.startsWith(n.to),
  );

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  return (
    <div className="flex h-full">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <aside className="hidden w-60 shrink-0 flex-col gap-6 border-r border-line bg-surface py-4 md:flex">
        <Brand />
        <nav aria-label="Primary" className="px-2">
          <NavItems />
        </nav>
      </aside>

      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/50"
            onClick={() => setDrawer(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col gap-6 border-r border-line bg-surface py-4">
            <div className="flex items-center justify-between pr-2">
              <Brand />
              <button
                type="button"
                aria-label="Close navigation"
                onClick={() => setDrawer(false)}
                className="rounded p-1 text-muted hover:bg-surface-2"
              >
                <X className="size-4" />
              </button>
            </div>
            <nav aria-label="Primary mobile" className="px-2">
              <NavItems onNavigate={() => setDrawer(false)} />
            </nav>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b border-line bg-surface/80 px-4 backdrop-blur">
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setDrawer(true)}
            className="rounded p-1.5 text-muted hover:bg-surface-2 md:hidden"
          >
            <Menu className="size-5" />
          </button>
          <nav aria-label="Breadcrumb" className="text-sm text-muted">
            <ol className="flex items-center gap-1.5">
              <li>EmojiLens</li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-fg">
                {current?.label ?? "Not found"}
              </li>
            </ol>
          </nav>
          <div className="ml-auto">
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="rounded-md border border-line p-1.5 text-muted hover:bg-surface-2 hover:text-fg"
            >
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
          </div>
        </header>
        <main id="main" className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
