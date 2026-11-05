"use client";

import { useEffect, useRef } from "react";

const COLORS = ["#7c5cff", "#22d3ee", "#f472b6", "#fbbf24", "#34d399"];

export function Confetti({ fire, duration = 2600 }: { fire: boolean; duration?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!fire) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    ctx.scale(dpr, dpr);

    const particles = Array.from({ length: 140 }, () => ({
      x: window.innerWidth * (0.3 + Math.random() * 0.4),
      y: window.innerHeight * 0.28 + Math.random() * 40,
      vx: (Math.random() - 0.5) * 9,
      vy: -Math.random() * 9 - 3,
      size: 4 + Math.random() * 6,
      rotation: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.25,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      life: 0,
    }));

    let frame = 0;
    let running = true;
    const start = performance.now();

    function tick(now: number) {
      if (!running || !ctx) return;
      const elapsed = now - start;
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      for (const particle of particles) {
        particle.vy += 0.22;
        particle.vx *= 0.995;
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.rotation += particle.vr;
        particle.life += 1;
        const alpha = Math.max(0, 1 - elapsed / duration);
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(particle.x, particle.y);
        ctx.rotate(particle.rotation);
        ctx.fillStyle = particle.color;
        ctx.fillRect(-particle.size / 2, -particle.size / 2, particle.size, particle.size * 0.6);
        ctx.restore();
      }
      frame = requestAnimationFrame(tick);
      if (elapsed > duration) {
        running = false;
        cancelAnimationFrame(frame);
        ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      }
    }
    frame = requestAnimationFrame(tick);
    return () => {
      running = false;
      cancelAnimationFrame(frame);
    };
  }, [fire, duration]);

  if (!fire) return null;
  return (
    <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-[70]" />
  );
}
