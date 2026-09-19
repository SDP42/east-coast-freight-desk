import { useEffect, useRef } from "react";
import * as THREE from "three";
import { createStage, project } from "./stage";

export interface Chokepoint { name: string; lat: number; lon: number; ratio: number | null; recent_per_day: number; baseline_per_day: number }
interface Props {
  chokepoints: Chokepoint[];
  lanes: Record<string, number[][]>;
  selected: string | null;
  onSelect: (name: string) => void;
  className?: string;
}

const R = 10;
const PORTS: [string, number, number][] = [["Paradip", 20.26, 86.67], ["Visakhapatnam", 17.69, 83.29], ["Dhamra", 20.79, 86.94], ["Gopalpur", 19.26, 84.91], ["Haldia", 22.03, 88.06]];
const LANE_COLOR: Record<string, number> = { Australia: 0x0e7490, Indonesia: 0x059669, Mozambique: 0xd97706, Russia: 0x7c3aed, "United States (Suez)": 0xdc2626, "United States (Cape)": 0xf97316 };

const ll = (lat: number, lon: number, r = R): THREE.Vector3 => {
  const phi = ((90 - lat) * Math.PI) / 180, th = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
};

function arc(a: THREE.Vector3, b: THREE.Vector3, steps: number, lift: number): THREE.Vector3[] {
  const out: THREE.Vector3[] = [];
  const na = a.clone().normalize(), nb = b.clone().normalize();
  const ang = na.angleTo(nb) || 1e-6;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const v = na.clone().multiplyScalar(Math.sin((1 - t) * ang) / Math.sin(ang)).add(nb.clone().multiplyScalar(Math.sin(t * ang) / Math.sin(ang)));
    out.push(v.multiplyScalar(R + Math.sin(Math.PI * t) * lift * ang));
  }
  return out;
}

/** Vanilla three.js globe: land dots, animated sea lanes with ships, and pulsing chokepoint markers coloured by traffic. */
export default function GlobeScene({ chokepoints, lanes, selected, onSelect, className = "" }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const selRef = useRef(selected);
  selRef.current = selected;
  const pick = useRef(onSelect);
  pick.current = onSelect;

  useEffect(() => {
    const el = host.current, labelHost = labels.current;
    if (!el || !labelHost) return;
    const stage = createStage(el, { fov: 38, position: [4, 12, 26], autoRotate: 0.35, minDistance: 16, maxDistance: 60, background: null });
    const { scene, camera } = stage;
    scene.add(new THREE.AmbientLight(0xffffff, 1.2));

    // Ocean sphere + soft atmosphere.
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(R - 0.04, 64, 48), new THREE.MeshBasicMaterial({ color: 0xd9ebf7 })));
    const grid = new THREE.Mesh(new THREE.SphereGeometry(R - 0.02, 36, 18), new THREE.MeshBasicMaterial({ color: 0xb5d3ea, wireframe: true, transparent: true, opacity: 0.35 }));
    scene.add(grid);
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.12, 48, 32), new THREE.ShaderMaterial({
      transparent: true, side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false,
      vertexShader: "varying vec3 n; void main(){ n = normalize(normalMatrix*normal); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ",
      fragmentShader: "varying vec3 n; void main(){ float i = pow(0.62 - dot(n, vec3(0,0,1.0)), 3.0); gl_FragColor = vec4(0.35,0.72,0.95,1.0)*i*1.4; }",
    })));

    // Land dots (Natural Earth 110m, public domain), loaded from /land_points.json.
    let landPoints: THREE.Points | null = null;
    fetch("/land_points.json").then((r) => r.json()).then((pts: [number, number][]) => {
      const pos = new Float32Array(pts.length * 3);
      pts.forEach(([lat, lon], i) => { const v = ll(lat, lon, R + 0.01); pos.set([v.x, v.y, v.z], i * 3); });
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      landPoints = new THREE.Points(g, new THREE.PointsMaterial({ color: 0x64748b, size: 0.17, sizeAttenuation: true }));
      scene.add(landPoints);
    }).catch(() => undefined);

    // Lanes and ships.
    const ships: { mesh: THREE.Mesh; path: THREE.Vector3[]; speed: number; offset: number }[] = [];
    Object.entries(lanes).forEach(([name, wps]) => {
      const pts: THREE.Vector3[] = [];
      const points = [...wps, [20.0, 87.0]];
      for (let i = 0; i < points.length - 1; i++) pts.push(...arc(ll(points[i][0], points[i][1]), ll(points[i + 1][0], points[i + 1][1]), 28, 0.9));
      const color = LANE_COLOR[name] ?? 0x0e7490;
      scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 })));
      const first = points[0];
      const origin = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 12), new THREE.MeshBasicMaterial({ color }));
      origin.position.copy(ll(first[0], first[1], R + 0.05));
      scene.add(origin);
      for (let k = 0; k < 3; k++) {
        const ship = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 10), new THREE.MeshBasicMaterial({ color: 0xffffff }));
        scene.add(ship);
        ships.push({ mesh: ship, path: pts, speed: 0.045 + Math.random() * 0.01, offset: k / 3 });
      }
    });

    // Destination ports.
    const portMat = new THREE.MeshBasicMaterial({ color: 0x0b2545 });
    PORTS.forEach(([, lat, lon]) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 10), portMat); m.position.copy(ll(lat, lon, R + 0.05)); scene.add(m); });

    // Chokepoints.
    const markers: { name: string; core: THREE.Mesh; ring: THREE.Mesh; pos: THREE.Vector3; el: HTMLDivElement; ratio: number }[] = [];
    chokepoints.forEach((c) => {
      const ratio = c.ratio ?? 1;
      const color = ratio < 0.75 ? 0xdc2626 : ratio < 0.95 ? 0xd97706 : ratio > 1.2 ? 0x0e7490 : 0x059669;
      const pos = ll(c.lat, c.lon, R + 0.08);
      const core = new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 16), new THREE.MeshBasicMaterial({ color }));
      core.position.copy(pos);
      core.userData.name = c.name;
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.3, 0.38, 32), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.7, side: THREE.DoubleSide }));
      ring.position.copy(pos);
      ring.lookAt(pos.clone().multiplyScalar(2));
      scene.add(core, ring);
      const el = document.createElement("div");
      el.className = "absolute -translate-x-1/2 whitespace-nowrap rounded-full border border-border-soft bg-white/90 px-2 py-0.5 text-[10px] font-medium text-strong shadow-sm backdrop-blur pointer-events-none";
      el.textContent = c.name.replace(" Strait", "").replace(" Canal", "");
      labelHost.appendChild(el);
      markers.push({ name: c.name, core, ring, pos, el, ratio });
    });

    // Aim at India at start.
    const home = ll(18, 72, 38);
    camera.position.copy(home);
    stage.controls.update();

    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onClick = (e: MouseEvent) => {
      const r = stage.renderer.domElement.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(mouse, camera);
      const hit = ray.intersectObjects(markers.map((m) => m.core))[0];
      if (hit) pick.current(hit.object.userData.name as string);
    };
    stage.renderer.domElement.addEventListener("click", onClick);
    let moved = 0;
    stage.renderer.domElement.addEventListener("pointerdown", () => { moved = 0; stage.controls.autoRotate = false; });
    stage.renderer.domElement.addEventListener("pointermove", () => { moved++; });
    void moved;

    stage.onFrame((t) => {
      ships.forEach((s) => {
        const u = (t * s.speed + s.offset) % 1;
        const idx = Math.floor(u * (s.path.length - 1));
        s.mesh.position.copy(s.path[idx]);
      });
      markers.forEach((m) => {
        const k = (t * 0.8) % 1;
        m.ring.scale.setScalar(1 + k * 2.2);
        (m.ring.material as THREE.MeshBasicMaterial).opacity = 0.75 * (1 - k);
        m.core.scale.setScalar(m.name === selRef.current ? 1.5 + Math.sin(t * 6) * 0.15 : 1);
        const visible = m.pos.clone().normalize().dot(camera.position.clone().normalize()) > 0.15;
        const p = project(m.pos, camera, el.clientWidth, el.clientHeight);
        if (p && visible) { m.el.style.left = `${p.x}px`; m.el.style.top = `${p.y - 18}px`; m.el.style.opacity = "1"; } else m.el.style.opacity = "0";
      });
      if (landPoints) landPoints.rotation.y = 0;
    });

    return () => { stage.renderer.domElement.removeEventListener("click", onClick); markers.forEach((m) => m.el.remove()); stage.dispose(); };
  }, [chokepoints, lanes]);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div ref={host} className="absolute inset-0 cursor-grab active:cursor-grabbing" />
      <div ref={labels} className="pointer-events-none absolute inset-0" />
    </div>
  );
}
