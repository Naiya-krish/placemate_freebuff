import { describe, expect, it } from "vitest";
import {
  clamp,
  cn,
  formatBytes,
  formatCurrency,
  formatDuration,
  initials,
  readinessBand,
  roundLabel,
  scoreTone,
} from "@/lib/utils";

describe("readinessBand", () => {
  it("maps thresholds to student-facing labels", () => {
    expect(readinessBand(90).label).toBe("Exceptional");
    expect(readinessBand(70).label).toBe("Interview-ready");
    expect(readinessBand(55).label).toBe("Building");
    expect(readinessBand(30).label).toBe("Warming up");
    expect(readinessBand(0).label).toBe("Getting started");
  });
});

describe("formatters", () => {
  it("formats bytes and durations", () => {
    expect(formatBytes(900)).toBe("900 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatDuration(65)).toBe("01:05");
    expect(formatDuration(-10)).toBe("00:00");
  });

  it("formats currency and initials", () => {
    expect(formatCurrency(0.0042)).toContain("0.0042");
    expect(initials("Aarav Sharma")).toBe("AS");
    expect(initials("Priya")).toBe("P");
  });

  it("labels roles and rounds", () => {
    expect(roundLabel("hr")).toBe("HR & behavioural");
    expect(roundLabel("unknown")).toBe("Interview");
  });
});

describe("helpers", () => {
  it("clamps values and merges classes", () => {
    expect(clamp(120)).toBe(100);
    expect(clamp(-3)).toBe(0);
    expect(cn("px-2", "px-4", false && "hidden")).toBe("px-4");
  });

  it("tone reflects score quality", () => {
    expect(scoreTone(82)).toBe("text-success");
    expect(scoreTone(60)).toBe("text-primary");
    expect(scoreTone(35)).toBe("text-warning");
    expect(scoreTone(10)).toBe("text-danger");
  });
});
