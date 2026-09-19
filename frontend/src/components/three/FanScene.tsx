import { useEffect, useRef } from "react";
import * as THREE from "three";
import { createStage, project } from "./stage";

export interface FanData {
  history: number[];
  paths: number[][];
  percentiles: Record<string, number[]>;
  last_value: number;
  horizon: number;
}

/** Vanilla three.js Monte-Carlo fan: the last 90 days of history, then 150 simulated futures drawn in depth,
 * with a translucent 5-95% ribbon and a bold median. Orbit with the mouse; paths draw in on load. */
export default function FanScene({ data, className = "" }: { data: FanData; className?: string }) {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = host.current, labelHost = labels.current;
    if (!el || !labelHost) return;
    const stage = createStage(el, { fov: 42, position: [-48, 40, 96], autoRotate: 0.5, minDistance: 30, maxDistance: 200, background: null });
    const { scene } = stage;
    scene.add(new THREE.AmbientLight(0xffffff, 1));

    const nH = data.history.length, nF = data.horizon;
    const all = [...data.history, ...data.paths.flat(), ...data.percentiles["5"], ...data.percentiles["95"]];
    const lo = Math.min(...all), hi = Math.max(...all);
    const X = (i: number) => ((i - nH) / (nH + nF)) * 110 + 10; // "now" sits near x = 10
    const Y = (v: number) => ((v - lo) / (hi - lo || 1)) * 38;

    // Floor grid and "now" plane.
    const floor = new THREE.GridHelper(120, 24, 0xb8cde0, 0xd7e3ee);
    floor.position.set(20, -0.1, 0);
    scene.add(floor);
    const now = new THREE.Mesh(new THREE.PlaneGeometry(50, 40), new THREE.MeshBasicMaterial({ color: 0x0e7490, transparent: true, opacity: 0.07, side: THREE.DoubleSide }));
    now.position.set(X(nH), 19, 0);
    now.rotation.y = Math.PI / 2;
    scene.add(now);

    // History ribbon.
    const hist = data.history.map((v, i) => new THREE.Vector3(X(i), Y(v), 0));
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(hist), new THREE.LineBasicMaterial({ color: 0x0b2545 })));

    // Simulated paths, each at its own depth so the fan opens into a sheet.
    const lines: { line: THREE.Line; count: number }[] = [];
    data.paths.forEach((p, k) => {
      const z = ((k * 7919) % 100) / 100 * 44 - 22;
      const pts = [new THREE.Vector3(X(nH - 1), Y(data.history[nH - 1]), 0), ...p.map((v, i) => new THREE.Vector3(X(nH + i), Y(v), z * Math.min(1, (i + 1) / 12)))];
      const t = k / data.paths.length;
      const color = new THREE.Color().setHSL(0.52 - t * 0.43, 0.75, 0.5);
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.55 }));
      line.geometry.setDrawRange(0, 0);
      scene.add(line);
      lines.push({ line, count: pts.length });
    });

    // Percentile ribbon (5-95%) and median.
    const p5 = data.percentiles["5"], p95 = data.percentiles["95"], p50 = data.percentiles["50"];
    const verts: number[] = [];
    for (let i = 0; i < nF - 1; i++) {
      const a = new THREE.Vector3(X(nH + i), Y(p5[i]), 0), b = new THREE.Vector3(X(nH + i + 1), Y(p5[i + 1]), 0);
      const c = new THREE.Vector3(X(nH + i), Y(p95[i]), 0), d = new THREE.Vector3(X(nH + i + 1), Y(p95[i + 1]), 0);
      verts.push(...a.toArray(), ...b.toArray(), ...c.toArray(), ...b.toArray(), ...d.toArray(), ...c.toArray());
    }
    const bandGeo = new THREE.BufferGeometry();
    bandGeo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    scene.add(new THREE.Mesh(bandGeo, new THREE.MeshBasicMaterial({ color: 0xd97706, transparent: true, opacity: 0.22, side: THREE.DoubleSide })));
    const med = p50.map((v, i) => new THREE.Vector3(X(nH + i), Y(v), 0));
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(med), new THREE.LineBasicMaterial({ color: 0xd97706 })));
    const tip = new THREE.Mesh(new THREE.SphereGeometry(0.7, 16, 16), new THREE.MeshBasicMaterial({ color: 0xd97706 }));
    scene.add(tip);

    const tags = [
      { text: `Now ${Math.round(data.last_value).toLocaleString()}`, pos: new THREE.Vector3(X(nH - 1), Y(data.history[nH - 1]) + 3, 0) },
      { text: `95%: ${Math.round(p95[nF - 1]).toLocaleString()}`, pos: new THREE.Vector3(X(nH + nF - 1), Y(p95[nF - 1]) + 2, 0) },
      { text: `Median: ${Math.round(p50[nF - 1]).toLocaleString()}`, pos: new THREE.Vector3(X(nH + nF - 1), Y(p50[nF - 1]), 0) },
      { text: `5%: ${Math.round(p5[nF - 1]).toLocaleString()}`, pos: new THREE.Vector3(X(nH + nF - 1), Y(p5[nF - 1]) - 2, 0) },
    ].map((t) => {
      const d = document.createElement("div");
      d.className = "absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-full border border-border-soft bg-white/90 px-2 py-0.5 text-[10px] font-semibold text-strong shadow-sm backdrop-blur";
      d.textContent = t.text;
      labelHost.appendChild(d);
      return { ...t, el: d };
    });

    stage.controls.target.set(28, 16, 0);
    stage.onFrame((t) => {
      const reveal = Math.min(1, t / 2.6);
      const e = 1 - Math.pow(1 - reveal, 3);
      lines.forEach(({ line, count }, k) => line.geometry.setDrawRange(0, Math.floor(count * Math.min(1, e * (1 + (k % 5) * 0.05)))));
      const idx = Math.min(nF - 1, Math.floor(e * (nF - 1)));
      tip.position.copy(med[idx]);
      tip.scale.setScalar(1 + Math.sin(t * 5) * 0.15);
      tags.forEach((tg) => { const p = project(tg.pos, stage.camera, el.clientWidth, el.clientHeight); if (p) { tg.el.style.left = `${p.x}px`; tg.el.style.top = `${p.y}px`; tg.el.style.opacity = e > 0.85 ? "1" : "0"; } });
    });
    return () => { tags.forEach((t) => t.el.remove()); stage.dispose(); };
  }, [data]);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div ref={host} className="absolute inset-0 cursor-grab active:cursor-grabbing" />
      <div ref={labels} className="pointer-events-none absolute inset-0" />
    </div>
  );
}
