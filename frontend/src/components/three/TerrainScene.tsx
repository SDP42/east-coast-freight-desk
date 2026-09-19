import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { createStage, project } from "./stage";

export interface TerrainData { series: { key: string; label: string }[]; months: string[]; z: number[][] }

const UP = 4; // upsampling factor for a smooth surface

function sample(z: number[][], r: number, c: number): number {
  const R = z.length, C = z[0].length;
  const r0 = Math.min(R - 1, Math.max(0, Math.floor(r))), r1 = Math.min(R - 1, r0 + 1);
  const c0 = Math.min(C - 1, Math.max(0, Math.floor(c))), c1 = Math.min(C - 1, c0 + 1);
  const fr = r - r0, fc = c - c0;
  const s = (t: number) => t * t * (3 - 2 * t);
  const a = z[r0][c0] * (1 - s(fc)) + z[r0][c1] * s(fc);
  const b = z[r1][c0] * (1 - s(fc)) + z[r1][c1] * s(fc);
  return a * (1 - s(fr)) + b * s(fr);
}

/** Vanilla three.js "market terrain": each series is a ridge, height is how far it sits above its own average. */
export default function TerrainScene({ data, className = "" }: { data: TerrainData; className?: string }) {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ series: string; month: string; z: number } | null>(null);

  useEffect(() => {
    const el = host.current, labelHost = labels.current;
    if (!el || !labelHost) return;
    const stage = createStage(el, { fov: 40, position: [72, 52, 92], autoRotate: 0.35, minDistance: 30, maxDistance: 180, background: null });
    const { scene } = stage;
    scene.add(new THREE.AmbientLight(0xffffff, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(-30, 60, 40);
    scene.add(sun);

    const R = data.z.length, C = data.z[0].length;
    const nr = (R - 1) * UP + 1, nc = (C - 1) * UP + 1;
    const W = 100, D = 44;
    const geo = new THREE.PlaneGeometry(W, D, nc - 1, nr - 1);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    const colors = new Float32Array(pos.count * 3);
    const heights = new Float32Array(pos.count);
    const lowC = new THREE.Color(0x3b82c4), midC = new THREE.Color(0xe8f1f8), highC = new THREE.Color(0xd97706);
    for (let i = 0; i < nr; i++) {
      for (let j = 0; j < nc; j++) {
        const idx = i * nc + j;
        const h = sample(data.z, i / UP, j / UP);
        heights[idx] = h;
        const t = Math.max(-2.2, Math.min(2.2, h)) / 2.2;
        const col = t < 0 ? lowC.clone().lerp(midC, 1 + t) : midC.clone().lerp(highC, t);
        colors.set([col.r, col.g, col.b], idx * 3);
      }
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, metalness: 0, side: THREE.DoubleSide, flatShading: false }));
    scene.add(mesh);
    const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: 0x0b2545, wireframe: true, transparent: true, opacity: 0.07 }));
    scene.add(wire);

    const base = new THREE.Mesh(new THREE.PlaneGeometry(W + 6, D + 6), new THREE.MeshBasicMaterial({ color: 0xeaf1f8, transparent: true, opacity: 0.6, side: THREE.DoubleSide }));
    base.rotation.x = -Math.PI / 2;
    base.position.y = -6;
    scene.add(base);

    const tagFor = (text: string, cls: string) => { const d = document.createElement("div"); d.className = `absolute -translate-x-full -translate-y-1/2 whitespace-nowrap text-[10px] font-medium ${cls}`; d.textContent = text; labelHost.appendChild(d); return d; };
    const rowTags = data.series.map((s, i) => ({ el: tagFor(s.label, "text-body"), v: new THREE.Vector3(-W / 2 - 1.5, -5, (i / (R - 1) - 0.5) * D) }));
    const yearTags = data.months.map((m, j) => ({ m, j })).filter(({ m }) => m.slice(5, 7) === "01").map(({ m, j }) => ({ el: (() => { const d = tagFor(m.slice(0, 4), "text-muted !-translate-x-1/2"); return d; })(), v: new THREE.Vector3((j / (C - 1) - 0.5) * W, -5, D / 2 + 2.5) }));

    // Hover readout.
    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onMove = (e: PointerEvent) => {
      const r = stage.renderer.domElement.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(mouse, stage.camera);
      const hit = ray.intersectObject(mesh)[0];
      if (!hit) { setHover(null); return; }
      const j = Math.round(((hit.point.x / W) + 0.5) * (C - 1)), i = Math.round(((hit.point.z / D) + 0.5) * (R - 1));
      if (i >= 0 && i < R && j >= 0 && j < C) setHover({ series: data.series[i].label, month: data.months[j].slice(0, 7), z: data.z[i][j] });
    };
    stage.renderer.domElement.addEventListener("pointermove", onMove);

    // Rise animation: heights scale from flat.
    const orig = Float32Array.from(heights);
    stage.onFrame((t) => {
      const k = 1 - Math.pow(1 - Math.min(1, t / 1.8), 3);
      for (let v = 0; v < pos.count; v++) pos.setY(v, orig[v] * 5.2 * k);
      pos.needsUpdate = true;
      geo.computeVertexNormals();
      const w = el.clientWidth, h = el.clientHeight;
      [...rowTags, ...yearTags].forEach(({ el: e, v }) => { const p = project(v, stage.camera, w, h); if (p) { e.style.left = `${p.x}px`; e.style.top = `${p.y}px`; e.style.opacity = "1"; } else e.style.opacity = "0"; });
    });
    stage.controls.target.set(0, 3, 0);
    return () => { stage.renderer.domElement.removeEventListener("pointermove", onMove); [...rowTags, ...yearTags].forEach((t) => t.el.remove()); stage.dispose(); };
  }, [data]);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div ref={host} className="absolute inset-0 cursor-grab active:cursor-grabbing" />
      <div ref={labels} className="pointer-events-none absolute inset-0" />
      {hover && (
        <div className="pointer-events-none absolute left-4 top-4 rounded-xl border border-border-soft bg-white/95 px-3 py-2 text-xs shadow backdrop-blur">
          <p className="font-semibold text-strong">{hover.series} · {hover.month}</p>
          <p className={hover.z >= 0 ? "text-amber" : "text-cyan"}>{hover.z >= 0 ? "+" : ""}{hover.z.toFixed(2)} σ from its own average</p>
        </div>
      )}
    </div>
  );
}
