import type { ReactNode } from "react";

/** Endless horizontal ticker for logos/labels (reactbits.dev "Logo Loop" pattern). */
export default function Marquee({ items }: { items: ReactNode[] }) {
  return (
    <div className="relative w-full overflow-hidden">
      <div className="flex w-max animate-marquee gap-10">
        {[...items, ...items].map((it, i) => <div key={i} className="whitespace-nowrap">{it}</div>)}
      </div>
    </div>
  );
}
