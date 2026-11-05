import Link from "next/link";
import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative flex size-9 items-center justify-center overflow-hidden rounded-xl bg-brand-gradient text-sm font-black text-white shadow-[0_8px_24px_-10px_rgba(124,92,255,0.9)]",
        className,
      )}
    >
      <span className="relative z-10">P</span>
      <span className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.55),transparent_50%)]" />
    </span>
  );
}

export function Brand({ href = "/", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2.5"
      aria-label="PlaceMate home"
    >
      <BrandMark />
      {!compact ? (
        <span className="font-display text-lg font-semibold tracking-tight">
          Place<span className="gradient-text">Mate</span>
        </span>
      ) : null}
    </Link>
  );
}
