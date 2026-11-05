"use client";

import { useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Languages } from "lucide-react";
import { cn } from "@/lib/utils";

const LOCALES = [
  { code: "en", label: "EN", name: "English" },
  { code: "hi", label: "हिं", name: "हिन्दी" },
];

export function LocaleSwitcher({ className }: { className?: string }) {
  const locale = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function change(code: string) {
    document.cookie = `placemate_locale=${code}; path=/; max-age=31536000; samesite=lax`;
    startTransition(() => router.refresh());
  }

  return (
    <div
      className={cn(
        "flex items-center gap-0.5 rounded-xl border border-border bg-surface p-0.5",
        pending && "opacity-60",
        className,
      )}
      role="group"
      aria-label="Language"
    >
      <Languages className="ml-1.5 size-3.5 text-muted" aria-hidden />
      {LOCALES.map((item) => (
        <button
          key={item.code}
          type="button"
          onClick={() => change(item.code)}
          aria-pressed={locale === item.code}
          title={item.name}
          className={cn(
            "rounded-lg px-2 py-1 text-[11px] font-semibold transition-colors",
            locale === item.code ? "bg-card text-fg shadow-sm" : "text-muted hover:text-fg",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
