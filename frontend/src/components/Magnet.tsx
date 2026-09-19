import { useRef, type ReactNode } from "react";

/** Element gently pulled toward the cursor (reactbits.dev "Magnet" pattern). */
export default function Magnet({ children, strength = 0.25 }: { children: ReactNode; strength?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const move = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.transform = `translate(${(e.clientX - (r.left + r.width / 2)) * strength}px, ${(e.clientY - (r.top + r.height / 2)) * strength}px)`;
  };
  return (
    <div ref={ref} className="inline-block transition-transform duration-200 ease-out" onMouseMove={move}
      onMouseLeave={() => { if (ref.current) ref.current.style.transform = "translate(0,0)"; }}>
      {children}
    </div>
  );
}
