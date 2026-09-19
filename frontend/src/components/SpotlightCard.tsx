import { useRef, type MouseEvent, type ReactNode } from "react";

interface SpotlightCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: string;
}

/** Card with a cursor-tracked soft glow (reactbits.dev "Spotlight Card" pattern, reimplemented). */
export default function SpotlightCard({ children, className = "", glowColor = "14,116,144" }: SpotlightCardProps) {
  const ref = useRef<HTMLDivElement>(null);

  function handleMouseMove(e: MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--y", `${e.clientY - rect.top}px`);
  }

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      className={`group relative overflow-hidden rounded-2xl border border-border-soft bg-white/90 shadow-[0_1px_2px_rgba(15,42,67,0.04),0_8px_24px_-12px_rgba(15,42,67,0.12)] backdrop-blur ${className}`}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: `radial-gradient(360px circle at var(--x, 50%) var(--y, 50%), rgba(${glowColor}, 0.10), transparent 70%)` }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
