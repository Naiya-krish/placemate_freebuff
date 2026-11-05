import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(value);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function readinessBand(score: number): { label: string; tone: string } {
  if (score >= 85) return { label: "Exceptional", tone: "success" };
  if (score >= 70) return { label: "Interview-ready", tone: "success" };
  if (score >= 50) return { label: "Building", tone: "primary" };
  if (score >= 25) return { label: "Warming up", tone: "warning" };
  return { label: "Getting started", tone: "muted" };
}

export function scoreTone(score: number): string {
  if (score >= 70) return "text-success";
  if (score >= 50) return "text-primary";
  if (score >= 30) return "text-warning";
  return "text-danger";
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function clamp(value: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, value));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: value < 0.1 ? 4 : 2,
  }).format(value);
}

export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function roundLabel(round: string | undefined): string {
  switch (round) {
    case "project":
      return "Project deep-dive";
    case "technical":
      return "Technical basics";
    case "hr":
      return "HR & behavioural";
    default:
      return "Interview";
  }
}

export function roleLabel(role: string | undefined): string {
  switch (role) {
    case "swe":
      return "Software engineering";
    case "data":
      return "Data & AI";
    case "product":
      return "Product";
    case "core":
      return "Core engineering";
    default:
      return role ? role.toUpperCase() : "General";
  }
}
