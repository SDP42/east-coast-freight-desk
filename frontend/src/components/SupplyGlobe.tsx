import { useEffect, useRef } from "react";
import createGlobe from "cobe";

/**
 * Real Earth (cobe samples actual land) with the coking-coal supply lanes as arcs: loading ports on the left of the map,
 * the Bay of Bengal discharge ports on the right. Drag to spin; it eases to a stop and resumes turning on its own.
 */
const ORIGINS: { name: string; loc: [number, number] }[] = [
  { name: "Hay Point / Newcastle", loc: [-21.3, 149.3] },
  { name: "Richards Bay", loc: [-28.8, 32.1] },
  { name: "Nacala (Mozambique)", loc: [-14.5, 40.7] },
  { name: "Hampton Roads", loc: [36.9, -76.3] },
  { name: "Vostochny", loc: [42.9, 132.9] },
];
const PORTS: [number, number][] = [[20.3, 86.7], [17.7, 83.3], [22.0, 88.1], [20.8, 86.9]];

export default function SupplyGlobe({ size = 520 }: { size?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const drag = useRef({ down: false, x: 0, phi: 0.2 * Math.PI * 2, vel: 0 });

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const px = Math.min(window.devicePixelRatio || 1, 2);
    const globe = createGlobe(canvas, {
      devicePixelRatio: px, width: size * px, height: size * px, phi: drag.current.phi, theta: 0.28, dark: 0, diffuse: 1.15, scale: 1,
      mapSamples: 22000, mapBrightness: 5, baseColor: [0.86, 0.92, 0.96], markerColor: [0.06, 0.45, 0.58], glowColor: [0.82, 0.93, 1],
      markers: [...ORIGINS.map((o) => ({ location: o.loc, size: 0.045 })), ...PORTS.map((p) => ({ location: p, size: 0.06, color: [0.85, 0.35, 0.06] as [number, number, number] }))],
      arcs: ORIGINS.flatMap((o) => PORTS.slice(0, 2).map((p) => ({ from: o.loc, to: p, color: [0.06, 0.45, 0.58] as [number, number, number] }))),
      arcColor: [0.06, 0.45, 0.58], arcWidth: 0.5, arcHeight: 0.28, markerElevation: 0.02,
    });
    let raf = 0;
    const loop = () => {
      const d = drag.current;
      if (!d.down) { d.phi += reduced ? 0 : 0.0032 + d.vel; d.vel *= 0.95; }
      globe.update({ phi: d.phi });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); globe.destroy(); };
  }, [size]);

  const move = (x: number) => { const d = drag.current; if (d.down) { d.phi += (x - d.x) / 160; d.vel = (x - d.x) / 4000; d.x = x; } };
  return (
    <canvas
      ref={ref} width={size * 2} height={size * 2} style={{ width: "100%", maxWidth: size, aspectRatio: "1", cursor: "grab", touchAction: "pan-y" }}
      onPointerDown={(e) => { drag.current.down = true; drag.current.x = e.clientX; (e.target as HTMLElement).setPointerCapture(e.pointerId); }}
      onPointerUp={() => { drag.current.down = false; }} onPointerMove={(e) => move(e.clientX)} aria-label="Globe of coking-coal supply lanes to India's East Coast ports"
    />
  );
}
