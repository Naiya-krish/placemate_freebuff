"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Brand } from "@/components/brand";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { ThemeToggle } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  const t = useTranslations("auth");
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 md:px-6">
        <Brand />
        <nav className="hidden items-center gap-6 text-sm text-muted md:flex" aria-label="Primary">
          <a href="#features" className="transition-colors hover:text-fg">
            Features
          </a>
          <a href="#how" className="transition-colors hover:text-fg">
            How it works
          </a>
          <a href="#privacy" className="transition-colors hover:text-fg">
            Privacy
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <LocaleSwitcher className="hidden sm:flex" />
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link href="/login">{t("signIn")}</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/signup">{t("signUp")}</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
