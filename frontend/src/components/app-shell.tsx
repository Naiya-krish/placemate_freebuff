"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  LogOut,
  MessagesSquare,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Brand, BrandMark } from "@/components/brand";
import { CommandPalette } from "@/components/command-palette";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Progress } from "@/components/ui/progress";
import { api, logout } from "@/lib/api";
import type { Usage, User } from "@/lib/types";
import { cn, formatCurrency, initials } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

export function AppShell({ user, children }: { user: User; children: React.ReactNode }) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();

  const nav: NavItem[] =
    user.role === "student"
      ? [
          { label: t("overview"), href: "/dashboard", icon: LayoutDashboard },
          { label: t("resume"), href: "/dashboard/resume", icon: FileText },
          { label: t("interviews"), href: "/dashboard/interviews", icon: MessagesSquare },
          { label: t("settings"), href: "/settings", icon: Settings },
        ]
      : user.role === "officer"
        ? [
            { label: t("analytics"), href: "/officer", icon: BarChart3 },
            { label: t("settings"), href: "/settings", icon: Settings },
          ]
        : [
            { label: t("admin"), href: "/admin", icon: ShieldCheck },
            { label: t("analytics"), href: "/officer", icon: BarChart3 },
            { label: t("settings"), href: "/settings", icon: Settings },
          ];

  const usageQuery = useQuery<Usage>({
    queryKey: ["usage"],
    queryFn: () => api.get<Usage>("/usage/me"),
    retry: false,
  });
  const usage = usageQuery.data;

  async function signOut() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  const roleLabel =
    user.role === "officer" ? "Placement officer" : user.role === "admin" ? "Admin" : "Student";

  return (
    <div className="min-h-dvh bg-bg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[90] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border/70 bg-surface/50 px-4 py-5 backdrop-blur-xl lg:flex">
        <div className="px-1.5">
          <Brand
            href={
              user.role === "student" ? "/dashboard" : user.role === "admin" ? "/admin" : "/officer"
            }
          />
        </div>
        <div className="mt-5 rounded-xl border border-border/80 bg-card/70 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
            {roleLabel}
          </p>
          <p className="mt-1 truncate text-sm font-semibold">{user.name}</p>
          {user.branch ? <p className="text-xs text-muted">{user.branch}</p> : null}
        </div>

        <nav className="mt-6 flex flex-1 flex-col gap-1" aria-label="Primary">
          {nav.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-brand-gradient text-white shadow-[0_8px_24px_-14px_rgba(124,92,255,0.9)]"
                    : "text-muted hover:bg-card hover:text-fg",
                )}
              >
                <Icon className="size-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="space-y-3">
          <div className="rounded-xl border border-border/80 bg-card/60 p-3">
            <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-muted">
              <span className="flex items-center gap-1">
                <Sparkles className="size-3" /> AI budget
              </span>
              {usage ? <span>{usage.percent_used}%</span> : null}
            </div>
            <Progress
              value={usage?.percent_used ?? 0}
              className="mt-2 h-1.5"
              label="Monthly AI budget used"
            />
            <p className="mt-2 text-[11px] text-muted">
              {usage
                ? `${formatCurrency(usage.remaining_usd)} / ${formatCurrency(usage.budget_usd)}`
                : "—"}
            </p>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex size-9 items-center justify-center rounded-full bg-brand-gradient text-xs font-bold text-white">
                {initials(user.name)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold">{user.name}</p>
                <p className="truncate text-[10px] text-muted">{user.email}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={signOut}
              aria-label="Sign out"
              title="Sign out"
              className="rounded-lg p-2 text-muted transition-colors hover:bg-card hover:text-danger"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 border-b border-border/70 bg-bg/85 backdrop-blur-xl lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Link
            href={
              user.role === "student" ? "/dashboard" : user.role === "admin" ? "/admin" : "/officer"
            }
          >
            <span className="flex items-center gap-2">
              <BrandMark className="size-8" />
              <span className="font-display text-base font-semibold">
                Place<span className="gradient-text">Mate</span>
              </span>
            </span>
          </Link>
          <div className="flex items-center gap-1.5">
            <LocaleSwitcher className="hidden sm:flex" />
            <ThemeToggle className="flex size-9 items-center justify-center rounded-xl border border-border bg-surface text-muted" />
            <span className="flex size-9 items-center justify-center rounded-full bg-brand-gradient text-[11px] font-bold text-white">
              {initials(user.name)}
            </span>
          </div>
        </div>
      </header>

      <div className="lg:pl-64">
        <div className="mx-auto w-full max-w-7xl px-4 pb-28 pt-4 md:px-6 lg:px-8 lg:pb-12 lg:pt-6">
          <div className="mb-5 hidden items-center justify-between gap-3 lg:flex">
            <CommandPalette role={user.role} />
            <div className="flex items-center gap-2">
              <LocaleSwitcher />
              <ThemeToggle />
            </div>
          </div>
          <main id="main">{children}</main>
        </div>
      </div>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border/80 bg-bg/90 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
        aria-label="Mobile navigation"
      >
        <div className="mx-auto flex max-w-md items-stretch justify-around">
          {nav.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-1 flex-col items-center gap-1 px-2 py-2.5 text-[10px] font-medium",
                  active ? "text-accent" : "text-muted",
                )}
              >
                <Icon
                  className={cn("size-5", active && "drop-shadow-[0_0_12px_rgba(34,211,238,0.6)]")}
                />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export function PageHeading({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? (
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function FullPageLoader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg">
      <div className="flex items-center gap-3 text-sm text-muted">
        <span className="size-2 animate-pulse rounded-full bg-primary" />
        {label}…
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="surface-card flex flex-col items-center gap-3 py-10 text-center">
      <p className="text-sm font-semibold text-danger">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
