import { useEffect, useRef } from "react";
import * as THREE from "three";
import { Water } from "three/examples/jsm/objects/Water.js";
import { createFx } from "./HaldiaFx";
import { makeBulker } from "./ShipModel";

interface Props {
  onPhase?: (phase: number) => void;
  className?: string;
}

const CYCLE = 46;
const LABELS = [
  { id: "anchor", text: "Sandheads anchorage · 130 km", phase: 0, pos: new THREE.Vector3(-78, 6, -24) },
  { id: "barge", text: "Floating crane · lightering", phase: 0, pos: new THREE.Vector3(-58, 5, -19) },
  { id: "river", text: "River Hooghly", phase: 1, pos: new THREE.Vector3(-25, 3, -25) },
  { id: "lock", text: "Lock gate · 330 × 39 m", phase: 2, pos: new THREE.Vector3(20, 6, -13) },
  { id: "berth", text: "Berth 4A · 2 grab unloaders", phase: 3, pos: new THREE.Vector3(6, 9, 44) },
  { id: "rail", text: "Rail to SAIL plants", phase: 4, pos: new THREE.Vector3(58, 4, 56) },
  { id: "oil", text: "Oil jetties", phase: -1, pos: new THREE.Vector3(48, 4, -11) },
];

function makeCrane(): THREE.Group {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0xe0a100, roughness: 0.6 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x40485a });
  for (const dx of [-1.4, 1.4]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.35, 6, 0.35), mat);
    leg.position.set(dx, 3, 0);
    leg.castShadow = true;
    g.add(leg);
  }
  const beam = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.4, 0.5), mat);
  beam.position.y = 6;
  g.add(beam);
  const boom = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.35, 9), mat);
  boom.position.set(0, 6.4, -4);
  boom.castShadow = true;
  g.add(boom);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.8, 0.9), dark);
  cab.position.set(0, 6.6, 0.4);
  g.add(cab);
  return g;
}

export default function HaldiaScene({ onPhase, className = "" }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const labelsRef = useRef<HTMLDivElement>(null);
  const onPhaseRef = useRef(onPhase);
  onPhaseRef.current = onPhase;

  useEffect(() => {
    const mount = mountRef.current;
    const labelHost = labelsRef.current;
    if (!mount || !labelHost) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const skyColor = new THREE.Color(0xeaf4fb);
    scene.fog = new THREE.Fog(skyColor, 140, 330);

    const camera = new THREE.PerspectiveCamera(30, 1, 1, 600);
    const camTarget = new THREE.Vector3(-6, 0, 12);

    const hemi = new THREE.HemisphereLight(0xffffff, 0xd6e6f2, 1.1);
    scene.add(hemi);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    const sun = new THREE.DirectionalLight(0xfff4e0, 1.9);
    sun.position.set(-60, 90, 50);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1536, 1536);
    Object.assign(sun.shadow.camera, { left: -110, right: 110, top: 90, bottom: -90, near: 10, far: 260 });
    scene.add(sun);

    // Water: three.js physically-based Water (mirror reflection of the sky and ships, Fresnel, sun glitter) driven by a
    // tileable procedural normal map, so no external texture is needed.
    const NS = 256;
    const nd = new Uint8Array(NS * NS * 4);
    const hgt = (x: number, y: number) => {
      const u = (x / NS) * Math.PI * 2, v = (y / NS) * Math.PI * 2;
      return Math.sin(u * 3 + v * 2) * 0.5 + Math.sin(u * 5 - v * 4 + 1.3) * 0.32 + Math.sin(u * 9 + v * 7 + 2.1) * 0.2 + Math.sin(u * 14 - v * 11) * 0.12;
    };
    for (let y = 0; y < NS; y++) for (let x = 0; x < NS; x++) {
      const dx = (hgt(x + 1, y) - hgt(x - 1, y)) * 1.5, dy = (hgt(x, y + 1) - hgt(x, y - 1)) * 1.5;
      const len = Math.hypot(dx, dy, 1), i = (y * NS + x) * 4;
      nd[i] = Math.round((-dx / len * 0.5 + 0.5) * 255); nd[i + 1] = Math.round((-dy / len * 0.5 + 0.5) * 255); nd[i + 2] = Math.round((1 / len * 0.5 + 0.5) * 255); nd[i + 3] = 255;
    }
    const normalTex = new THREE.DataTexture(nd, NS, NS, THREE.RGBAFormat);
    normalTex.wrapS = normalTex.wrapT = THREE.RepeatWrapping;
    normalTex.needsUpdate = true;
    const water = new Water(new THREE.PlaneGeometry(520, 420), {
      textureWidth: 512, textureHeight: 512, waterNormals: normalTex, sunDirection: sun.position.clone().normalize(),
      sunColor: 0xfff1d6, waterColor: 0x0c6a80, distortionScale: 0.55, fog: true,
    });
    // Less mirror, more body colour: an estuary reads as deep green-blue water, not polished metal.
    (water.material as THREE.ShaderMaterial).onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace(
        "float reflectance = rf0 + ( 1.0 - rf0 ) * pow( ( 1.0 - theta ), 5.0 );",
        "float reflectance = rf0 + ( 1.0 - rf0 ) * pow( ( 1.0 - theta ), 5.0 ); reflectance = reflectance * 0.45 + 0.04;",
      );
    };
    water.rotation.x = -Math.PI / 2;
    water.position.y = -0.05;
    (water.material as THREE.ShaderMaterial).uniforms.size.value = 5;
    scene.add(water);

    const sand = new THREE.MeshStandardMaterial({ color: 0xb5a98f, roughness: 1 });
    const concrete = new THREE.MeshStandardMaterial({ color: 0x9aa2aa, roughness: 0.9 });
    const green = new THREE.MeshStandardMaterial({ color: 0x5f7a55, roughness: 1 });
    const landBox = (x0: number, x1: number, z0: number, z1: number, mat: THREE.Material, h = 0.5) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, h, z1 - z0), mat);
      m.position.set((x0 + x1) / 2, h / 2 - 0.05, (z0 + z1) / 2);
      m.receiveShadow = true;
      scene.add(m);
      return m;
    };
    landBox(-300, 18.05, -14, 19, sand);
    landBox(21.95, 300, -14, 19, sand);
    landBox(-300, -30, 19, 200, sand);
    landBox(60, 300, 19, 200, sand);
    landBox(-30, 60, 46, 200, sand);
    landBox(-300, 300, -200, -34, green);
    // Quay edges.
    landBox(-30, 60, 45.4, 46, concrete, 0.7);
    landBox(18.0, 18.6, -14, 19, concrete, 0.7);
    landBox(21.4, 22.0, -14, 19, concrete, 0.7);

    // Lock gates (hinged flaps).
    const gateMat = new THREE.MeshStandardMaterial({ color: 0x35507a });
    const makeGate = (z: number) => {
      const pivot = new THREE.Group();
      pivot.position.set(18.05, 0.4, z);
      const leaf = new THREE.Mesh(new THREE.BoxGeometry(2.05, 1.1, 0.25), gateMat);
      leaf.position.x = 1.02;
      leaf.castShadow = true;
      pivot.add(leaf);
      const pivot2 = new THREE.Group();
      pivot2.position.set(21.95, 0.4, z);
      const leaf2 = new THREE.Mesh(new THREE.BoxGeometry(2.05, 1.1, 0.25), gateMat);
      leaf2.position.x = -1.02;
      leaf2.castShadow = true;
      pivot2.add(leaf2);
      scene.add(pivot, pivot2);
      return [pivot, pivot2] as const;
    };
    const gate1 = makeGate(-12);
    const gate2 = makeGate(17);
    const chamber = new THREE.Mesh(
      new THREE.PlaneGeometry(3.85, 27),
      new THREE.MeshBasicMaterial({ color: 0x9fe0ee, transparent: true, opacity: 0.55 }),
    );
    chamber.rotation.x = -Math.PI / 2;
    chamber.position.set(20, 0.1, 2.5);
    scene.add(chamber);

    // Oil jetty + tanker on the river bank.
    landBox(44, 52, -14, -12, concrete, 0.6);
    const tanker = makeBulker(0x2f4f4f, 0.8);
    tanker.position.set(48, 0.1, -19);
    scene.add(tanker);

    // Berths: static neighbour ship + cranes on berth 4A.
    const neighbour = makeBulker(0x35507a, 1);
    neighbour.position.set(36, 0.15, 42.6);
    neighbour.rotation.y = Math.PI;
    scene.add(neighbour);
    const cranes: THREE.Group[] = [];
    const grabs: THREE.Mesh[] = [];
    for (const x of [-2, 10]) {
      const c = makeCrane();
      c.position.set(x, 0, 47.4);
      scene.add(c);
      cranes.push(c);
      const grab = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.6, 0.7), new THREE.MeshStandardMaterial({ color: 0x222831 }));
      grab.position.set(x, 4, 43.2);
      scene.add(grab);
      grabs.push(grab);
    }
    // Coal stockyard.
    const coalMat = new THREE.MeshStandardMaterial({ color: 0x232830, roughness: 1, flatShading: true });
    const pile = new THREE.Mesh(new THREE.ConeGeometry(6, 4, 7), coalMat);
    pile.position.set(4, 0, 57);
    pile.castShadow = true;
    scene.add(pile);
    const pile2 = new THREE.Mesh(new THREE.ConeGeometry(4, 2.4, 6), coalMat);
    pile2.position.set(-14, 0, 56);
    scene.add(pile2);
    // Rail line and wagons.
    const rail = new THREE.Mesh(new THREE.BoxGeometry(220, 0.08, 0.5), new THREE.MeshStandardMaterial({ color: 0x64707f }));
    rail.position.set(60, 0.5, 66);
    scene.add(rail);
    const train = new THREE.Group();
    for (let i = 0; i < 12; i++) {
      const w = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.9, 1.3), new THREE.MeshStandardMaterial({ color: i === 0 ? 0x1f3a5f : 0x8a4b2d }));
      w.position.set(i * 2.5, 0.95, 0);
      w.castShadow = true;
      train.add(w);
    }
    train.position.set(20, 0, 66);
    scene.add(train);

    // Yard details: sheds, container stacks, chimney, road.
    const shedMat = new THREE.MeshStandardMaterial({ color: 0xf1f4f8, roughness: 0.8 });
    [[-44, 70, 14, 8], [-24, 74, 10, 6], [40, 80, 16, 8]].forEach(([x, z, w, d]) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, 3, d), shedMat);
      m.position.set(x, 1.5, z);
      m.castShadow = true;
      scene.add(m);
    });
    const boxCols = [0xd4574a, 0x3e7cb1, 0xe0a100, 0x4b9b7d];
    for (let i = 0; i < 14; i++) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.2, 1.1), new THREE.MeshStandardMaterial({ color: boxCols[i % 4] }));
      m.position.set(48 + (i % 7) * 2.6, 0.9 + Math.floor(i / 7) * 1.2, 58 + (i % 2) * 1.2);
      m.castShadow = true;
      scene.add(m);
    }
    const chimney = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.4, 16, 12), new THREE.MeshStandardMaterial({ color: 0xc8b8a4 }));
    chimney.position.set(84, 8, 36);
    chimney.castShadow = true;
    scene.add(chimney);
    const road = new THREE.Mesh(new THREE.BoxGeometry(220, 0.05, 3), new THREE.MeshStandardMaterial({ color: 0xa9b3bf }));
    road.position.set(0, 0.47, 52);
    scene.add(road);

    // Anchorage queue + floating crane barge.
    const anchored: THREE.Group[] = [];
    [[-92, -23, 0x8c2f39], [-78, -26.5, 0x35507a], [-66, -22, 0x2f6f5e]].forEach(([x, z, c], i) => {
      const s = makeBulker(c as number, 1);
      s.position.set(x as number, 0.15, z as number);
      s.rotation.y = Math.PI + (i - 1) * 0.06;
      scene.add(s);
      anchored.push(s);
    });
    const barge = new THREE.Group();
    const bargeHull = new THREE.Mesh(new THREE.BoxGeometry(5, 0.6, 2.4), new THREE.MeshStandardMaterial({ color: 0x556070 }));
    barge.add(bargeHull);
    const bargeBoom = new THREE.Mesh(new THREE.BoxGeometry(0.3, 4.5, 0.3), new THREE.MeshStandardMaterial({ color: 0xe0a100 }));
    bargeBoom.position.set(0, 2.4, 0);
    bargeBoom.rotation.z = 0.5;
    barge.add(bargeBoom);
    barge.position.set(-58, 0.1, -21);
    scene.add(barge);

    // The vessel that makes the trip.
    const hullColors = [0x8c2f39, 0x35507a, 0x2f6f5e, 0x6b4a8a, 0x1f2937];
    let hero = makeBulker(hullColors[0]);
    scene.add(hero);
    let heroColorIdx = 0;
    const fx = createFx(scene, sun, hemi);

    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-130, 0.15, -23.5),
      new THREE.Vector3(-40, 0.15, -23),
      new THREE.Vector3(4, 0.15, -22),
      new THREE.Vector3(16, 0.15, -17),
      new THREE.Vector3(20, 0.15, -10),
      new THREE.Vector3(20, 0.15, 2.5),
      new THREE.Vector3(20, 0.15, 14),
      new THREE.Vector3(20, 0.15, 24),
      new THREE.Vector3(18, 0.15, 33),
      new THREE.Vector3(12, 0.15, 39.5),
      new THREE.Vector3(6, 0.15, 42.7),
      new THREE.Vector3(3, 0.15, 42.8),
    ], false, "catmullrom", 0.4);
    const samples = curve.getSpacedPoints(600);
    const uAt = (pred: (p: THREE.Vector3) => number) => {
      let best = 0, bd = Infinity;
      samples.forEach((p, i) => { const d = pred(p); if (d < bd) { bd = d; best = i; } });
      return best / 600;
    };
    const uLockIn = uAt((p) => Math.abs(p.z - 2.5));
    const uBerth = 1;

    const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
    const ease = (t: number) => t * t * (3 - 2 * t);
    const heroU = (t: number): number => {
      if (t < 8) return ease(clamp01(t / 8)) * uLockIn;
      if (t < 16) return uLockIn;
      if (t < 23) return uLockIn + (uBerth - uLockIn) * ease((t - 16) / 7);
      if (t < 33) return uBerth;
      return uBerth * (1 - ease(clamp01((t - 33) / 13)));
    };
    const phaseAt = (t: number): number => {
      if (t < 4) return 0;
      if (t < 8) return 1;
      if (t < 16) return 2;
      if (t < 33) return 3;
      return 4;
    };

    // Labels.
    const labelEls = LABELS.map((l) => {
      const el = document.createElement("div");
      el.className = "absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-full border border-border-soft bg-white/90 px-2.5 py-1 text-[11px] font-medium text-strong shadow-sm backdrop-blur transition-opacity duration-500";
      el.textContent = l.text;
      labelHost.appendChild(el);
      return el;
    });

    const resize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(mount);

    const mouse = { x: 0, y: 0 };
    const onMove = (e: MouseEvent) => {
      const r = mount.getBoundingClientRect();
      mouse.x = ((e.clientX - r.left) / r.width - 0.5) * 2;
      mouse.y = ((e.clientY - r.top) / r.height - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMove);

    const clock = new THREE.Clock();
    let raf = 0;
    let lastPhase = -1;
    let heroYaw = 0;
    const tmpV = new THREE.Vector3();

    const setGate = (gate: readonly [THREE.Group, THREE.Group], open: number) => {
      gate[0].rotation.y = open * (Math.PI / 2.1) * -1;
      gate[1].rotation.y = open * (Math.PI / 2.1);
    };

    let lastTime = 0;
    const look = new THREE.Vector3(-6, 0, 12);
    const goalPos = new THREE.Vector3();
    const goalLook = new THREE.Vector3();
    const heroFwd = new THREE.Vector3();
    let fov = 30;
    const frame = () => {
      const time = clock.getElapsedTime();
      const dt = Math.min(0.1, time - lastTime);
      lastTime = time;
      const t = reduced ? 20 : time % CYCLE;
      (water.material as THREE.ShaderMaterial).uniforms.time.value = time * 0.5;
      (water.material as THREE.ShaderMaterial).uniforms.sunDirection.value.copy(sun.position).normalize();

      if (!reduced && t < 0.06 && Math.floor(time / CYCLE) !== heroColorIdx) {
        heroColorIdx = Math.floor(time / CYCLE);
        scene.remove(hero);
        hero = makeBulker(hullColors[heroColorIdx % hullColors.length]);
        scene.add(hero);
      }

      const u = clamp01(heroU(t));
      const p = curve.getPointAt(u);
      const inbound = t < 33;
      const tan = curve.getTangentAt(Math.min(0.999, Math.max(0.001, u)));
      const targetYaw = Math.atan2(-tan.z, tan.x) + (inbound ? 0 : Math.PI);
      let d = targetYaw - heroYaw;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      heroYaw += d * (1 - Math.exp(-4.5 * dt));
      hero.position.set(p.x, 0.15 + Math.sin(time * 1.3) * 0.03, p.z);
      hero.rotation.y = heroYaw;
      hero.rotation.z = Math.sin(time * 0.9) * 0.008;

      // Gates and lock chamber level.
      const g1 = t < 6 ? 1 : t < 9 ? 1 - ease((t - 6) / 3) : t < 33 ? 0 : 1;
      const g2 = t < 14 ? 0 : t < 17 ? ease((t - 14) / 3) : 1;
      setGate(gate1, g1);
      setGate(gate2, g2);
      const level = t < 9 ? 0 : t < 14 ? ease((t - 9) / 5) * 0.16 : 0.16;
      chamber.position.y = 0.06 + (t >= 33 ? 0.16 : level);

      // Unloading.
      const unloading = t >= 23 && t < 33;
      const prog = clamp01((t - 23) / 10);
      const pileScale = t < 23 ? 0.15 : t < 33 ? 0.15 + prog * 0.85 : 1;
      pile.scale.set(pileScale, pileScale, pileScale);
      grabs.forEach((gm, i) => {
        gm.position.y = unloading ? 3.2 + Math.abs(Math.sin(time * 1.6 + i * 1.7)) * 2.2 : 5;
        gm.position.z = unloading ? 43.2 + Math.sin(time * 0.8 + i) * 0.4 : 44.5;
      });

      // Train: loads, leaves east, an empty one returns.
      let trainX = 20;
      if (t >= 34 && t < 42) trainX = 20 + ease((t - 34) / 8) * 150;
      else if (t >= 42) trainX = -140 + ease((t - 42) / 4) * 160;
      else if (t < 4) trainX = 20;
      train.position.x = trainX;

      // Anchored ships and barge idle.
      anchored.forEach((s, i) => { s.position.y = 0.15 + Math.sin(time * 1.1 + i) * 0.04; s.rotation.z = Math.sin(time * 0.7 + i) * 0.01; });
      barge.position.y = 0.1 + Math.sin(time * 1.4) * 0.04;
      bargeBoom.rotation.z = 0.5 + Math.sin(time * 0.8) * 0.12;
      tanker.position.y = 0.1 + Math.sin(time * 1.2) * 0.03;

      // Camera director: wide establishing view, then follows the vessel through each stage.
      heroFwd.set(Math.cos(heroYaw), 0, -Math.sin(heroYaw));
      const side = new THREE.Vector3(-heroFwd.z, 0, heroFwd.x);
      const ang = 0.55 + mouse.x * 0.12;
      const wideMode = t < 3.5 || t >= 41 || reduced;
      let goalFov = 30;
      if (wideMode) {
        goalPos.set(Math.sin(ang) * 175 - 8, 108 - mouse.y * 10, Math.cos(ang) * 175 + 6);
        goalLook.copy(camTarget);
      } else if (t < 8) {
        goalPos.copy(hero.position).addScaledVector(heroFwd, -26).addScaledVector(side, 20).setY(15);
        goalLook.copy(hero.position).addScaledVector(heroFwd, 10);
        goalFov = 44;
      } else if (t < 16) {
        goalPos.set(48, 26, 30);
        goalLook.set(20, 1, 3);
        goalFov = 40;
      } else if (t < 23) {
        goalPos.copy(hero.position).addScaledVector(heroFwd, -20).addScaledVector(side, -18).setY(13);
        goalLook.copy(hero.position).addScaledVector(heroFwd, 6);
        goalFov = 44;
      } else if (t < 33) {
        goalPos.set(-14, 22, 78);
        goalLook.set(6, 4, 44);
        goalFov = 42;
      } else {
        goalPos.copy(hero.position).addScaledVector(heroFwd, -24).addScaledVector(side, 16).setY(16);
        goalLook.copy(hero.position);
        goalFov = 42;
      }
      camera.position.lerp(goalPos, 1 - Math.exp(-(wideMode ? 1.8 : 2.4) * dt));
      look.lerp(goalLook, 1 - Math.exp(-3.4 * dt));
      fov += (goalFov - fov) * (1 - Math.exp(-2.5 * dt));
      if (Math.abs(camera.fov - fov) > 0.01) { camera.fov = fov; camera.updateProjectionMatrix(); }
      camera.lookAt(look);

      fx.update({ time, dt, t, cycle01: t / CYCLE, hero, heroYaw, unloading, phase: phaseAt(t) });

      // Labels follow their anchors.
      const phase = phaseAt(t);
      if (phase !== lastPhase) { lastPhase = phase; onPhaseRef.current?.(phase); }
      const w = mount.clientWidth, h = mount.clientHeight;
      LABELS.forEach((l, i) => {
        tmpV.copy(l.pos).project(camera);
        const el = labelEls[i];
        const visible = tmpV.z < 1 && Math.abs(tmpV.x) < 1.05 && Math.abs(tmpV.y) < 1.05;
        el.style.left = `${(tmpV.x * 0.5 + 0.5) * w}px`;
        el.style.top = `${(-tmpV.y * 0.5 + 0.5) * h}px`;
        el.style.opacity = visible ? (l.phase === phase || l.phase === -1 ? "1" : "0.35") : "0";
      });

      renderer.render(scene, camera);
      if (!reduced) raf = requestAnimationFrame(frame);
    };
    frame();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("mousemove", onMove);
      labelEls.forEach((el) => el.remove());
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        const mat = m.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
        else mat?.dispose();
      });
      fx.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div ref={mountRef} className="absolute inset-0" />
      <div ref={labelsRef} className="pointer-events-none absolute inset-0" />
    </div>
  );
}
