"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  MessagesSquare,
  Search,
  Settings,
  ShieldCheck,
  SunMoon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useTheme } from "@/components/theme-provider";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Item {
  label: string;
  href?: string;
  icon: LucideIcon;
  action?: () => void;
  keywords?: string;
}

export function CommandPalette({ role }: { role: Role }) {
  const t = useTranslations("nav");
  const tc = useTranslations("common");
  const router = useRouter();
  const { toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const items = useMemo<Item[]>(() => {
    const base: Item[] = [
      {
        label: t("overview"),
        href: "/dashboard",
        icon: LayoutDashboard,
        keywords: "home readiness",
      },
      {
        label: t("resume"),
        href: "/dashboard/resume",
        icon: FileText,
        keywords: "upload score analysis",
      },
      {
        label: t("interviews"),
        href: "/dashboard/interviews",
        icon: MessagesSquare,
        keywords: "mock practice feedback",
      },
      { label: t("settings"), href: "/settings", icon: Settings, keywords: "privacy delete" },
    ];
    if (role === "officer" || role === "admin") {
      base.unshift({
        label: t("analytics"),
        href: "/officer",
        icon: BarChart3,
        keywords: "heatmap cohort funnel report",
      });
    }
    if (role === "admin") {
      base.unshift({
        label: t("admin"),
        href: "/admin",
        icon: ShieldCheck,
        keywords: "colleges questions rubrics",
      });
    }
    base.push({
      label: `Toggle theme`,
      icon: SunMoon,
      action: toggle,
      keywords: "dark light appearance",
    });
    return base;
  }, [role, t, toggle]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) =>
      `${item.label} ${item.keywords ?? ""}`.toLowerCase().includes(normalized),
    );
  }, [items, query]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
    }
  }, [open]);

  function run(item: Item) {
    setOpen(false);
    if (item.action) item.action();
    if (item.href) router.push(item.href);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, filtered.length - 1));
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    }
    if (event.key === "Enter" && filtered[active]) {
      event.preventDefault();
      run(filtered[active]);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-9 items-center gap-2 rounded-xl border border-border bg-surface/70 px-3 text-xs text-muted transition-colors hover:border-primary/40 hover:text-fg"
        aria-label={tc("command")}
      >
        <Search className="size-3.5" aria-hidden />
        <span className="hidden sm:inline">{tc("search")}…</span>
        <kbd className="ml-2 hidden rounded border border-border bg-card px-1.5 py-0.5 font-mono text-[10px] text-muted sm:inline">
          ⌘K
        </kbd>
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[80] flex items-start justify-center bg-black/70 px-4 pt-[12vh] backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label={tc("command")}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-border bg-card shadow-glow">
            <div className="flex items-center gap-3 border-b border-border px-4">
              <Search className="size-4 text-muted" aria-hidden />
              <input
                autoFocus
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActive(0);
                }}
                onKeyDown={onKeyDown}
                placeholder={`${tc("search")}…`}
                aria-label={tc("search")}
                className="h-12 flex-1 bg-transparent text-sm text-fg placeholder:text-muted focus:outline-none"
              />
              <kbd className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted">
                ESC
              </kbd>
            </div>
            <ul className="max-h-80 overflow-y-auto p-2" role="listbox">
              {filtered.length === 0 ? (
                <li className="px-3 py-6 text-center text-sm text-muted">No results</li>
              ) : (
                filtered.map((item, index) => {
                  const Icon = item.icon;
                  return (
                    <li key={`${item.label}-${index}`}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={index === active}
                        onMouseEnter={() => setActive(index)}
                        onClick={() => run(item)}
                        className={cn(
                          "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                          index === active ? "bg-surface text-fg" : "text-muted hover:text-fg",
                        )}
                      >
                        <Icon className="size-4" aria-hidden />
                        {item.label}
                      </button>
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        </div>
      ) : null}
    </>
  );
}
