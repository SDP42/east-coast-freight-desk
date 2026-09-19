import * as THREE from "three";

/** Soft-disc particle system: one draw call, per-particle alpha and size, used for wakes, smoke and dust. */
function particles(count: number, color: number, opacity: number, sizeScale = 1) {
  const pos = new Float32Array(count * 3), alpha = new Float32Array(count), size = new Float32Array(count);
  const vel = new Float32Array(count * 3), life = new Float32Array(count), maxLife = new Float32Array(count), s0 = new Float32Array(count), grow = new Float32Array(count);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("aAlpha", new THREE.BufferAttribute(alpha, 1));
  geo.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uColor: { value: new THREE.Color(color) }, uOpacity: { value: opacity }, uScale: { value: sizeScale * 260 } },
    vertexShader: "attribute float aAlpha; attribute float aSize; uniform float uScale; varying float vA; void main(){ vA = aAlpha; vec4 mv = modelViewMatrix*vec4(position,1.0); gl_PointSize = aSize * uScale / -mv.z; gl_Position = projectionMatrix*mv; }",
    fragmentShader: "uniform vec3 uColor; uniform float uOpacity; varying float vA; void main(){ float d = length(gl_PointCoord-0.5); if(d>0.5) discard; gl_FragColor = vec4(uColor, smoothstep(0.5,0.05,d)*vA*uOpacity); }",
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  let head = 0;
  return {
    points,
    spawn(x: number, y: number, z: number, vx: number, vy: number, vz: number, lifeSec: number, startSize: number, growth = 0) {
      const i = head; head = (head + 1) % count;
      pos.set([x, y, z], i * 3); vel.set([vx, vy, vz], i * 3);
      life[i] = maxLife[i] = lifeSec; s0[i] = startSize; grow[i] = growth;
    },
    update(dt: number) {
      for (let i = 0; i < count; i++) {
        if (life[i] <= 0) { alpha[i] = 0; continue; }
        life[i] -= dt;
        pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
        const k = Math.max(0, life[i] / maxLife[i]);
        alpha[i] = Math.min(1, (1 - k) * 8) * k;
        size[i] = s0[i] + grow[i] * (1 - k);
      }
      (geo.attributes.position as THREE.BufferAttribute).needsUpdate = true;
      (geo.attributes.aAlpha as THREE.BufferAttribute).needsUpdate = true;
      (geo.attributes.aSize as THREE.BufferAttribute).needsUpdate = true;
    },
  };
}

function cloudTexture(): THREE.Texture {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, "rgba(255,255,255,0.95)");
  grad.addColorStop(0.55, "rgba(255,255,255,0.45)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

export interface FxUpdate { time: number; dt: number; t: number; cycle01: number; hero: THREE.Object3D; heroYaw: number; unloading: boolean; phase: number }

export function createFx(scene: THREE.Scene, sun: THREE.DirectionalLight, hemi: THREE.HemisphereLight) {
  const disposables: { dispose: () => void }[] = [];

  // Sky dome with a warm horizon and a soft sun.
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { uTop: { value: new THREE.Color(0x9ccbef) }, uHorizon: { value: new THREE.Color(0xfff3dd) }, uSunDir: { value: new THREE.Vector3(-0.5, 0.7, 0.4).normalize() }, uSunColor: { value: new THREE.Color(0xfff0c9) } },
    vertexShader: "varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
    fragmentShader: "uniform vec3 uTop; uniform vec3 uHorizon; uniform vec3 uSunDir; uniform vec3 uSunColor; varying vec3 vDir; void main(){ float h = clamp(vDir.y, 0.0, 1.0); vec3 col = mix(uHorizon, uTop, pow(h, 0.55)); float s = max(dot(vDir, normalize(uSunDir)), 0.0); col += uSunColor * (pow(s, 900.0) * 1.2 + pow(s, 8.0) * 0.18); gl_FragColor = vec4(col, 1.0); }",
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(520, 32, 16), skyMat);
  scene.add(sky);
  disposables.push(sky.geometry, skyMat);

  // Drifting clouds.
  const cTex = cloudTexture();
  const clouds: THREE.Sprite[] = [];
  for (let i = 0; i < 16; i++) {
    const m = new THREE.SpriteMaterial({ map: cTex, transparent: true, opacity: 0.5 + (i % 3) * 0.1, depthWrite: false, fog: false });
    const s = new THREE.Sprite(m);
    const sc = 70 + (i * 37) % 80;
    s.scale.set(sc * 1.6, sc * 0.6, 1);
    s.position.set(-260 + (i * 61) % 520, 95 + (i * 23) % 45, -220 + (i * 47) % 260);
    scene.add(s);
    clouds.push(s);
    disposables.push(m);
  }
  disposables.push(cTex);

  // Particle systems.
  const foam = particles(700, 0xffffff, 0.8, 0.9), smoke = particles(360, 0x6b7280, 0.5, 1.2), dust = particles(220, 0x2b2f38, 0.6, 0.8), plume = particles(260, 0xf4f4f4, 0.55, 1.6);
  [foam, smoke, dust, plume].forEach((p) => { scene.add(p.points); disposables.push(p.points.geometry, p.points.material as THREE.Material); });

  // Tug boat.
  const tug = new THREE.Group();
  const tugHull = new THREE.Mesh(new THREE.BoxGeometry(3.4, 0.9, 1.5), new THREE.MeshStandardMaterial({ color: 0xe65c1f, roughness: 0.6 }));
  tugHull.position.y = 0.05;
  const tugCabin = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.9, 1.1), new THREE.MeshStandardMaterial({ color: 0xffffff }));
  tugCabin.position.set(-0.4, 0.95, 0);
  const tugStack = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.7, 8), new THREE.MeshStandardMaterial({ color: 0x1f2937 }));
  tugStack.position.set(-0.9, 1.6, 0);
  tug.add(tugHull, tugCabin, tugStack);
  tug.traverse((o) => { o.castShadow = true; });
  scene.add(tug);

  // Birds.
  const birdMat = new THREE.MeshBasicMaterial({ color: 0x334155, side: THREE.DoubleSide });
  const birds = Array.from({ length: 9 }, (_, i) => {
    const g = new THREE.Group();
    const wing = new THREE.PlaneGeometry(1.4, 0.35);
    const l = new THREE.Mesh(wing, birdMat), r = new THREE.Mesh(wing, birdMat);
    l.position.x = -0.7; r.position.x = 0.7;
    g.add(l, r);
    scene.add(g);
    return { g, l, r, radius: 34 + (i % 4) * 9, h: 24 + (i % 3) * 5, speed: 0.16 + (i % 5) * 0.02, phase: i * 0.7 };
  });
  disposables.push(birdMat);

  // Channel buoys (blinking).
  const buoys: { m: THREE.Mesh; mat: THREE.MeshStandardMaterial; k: number }[] = [];
  for (let i = 0; i < 12; i++) {
    const red = i % 2 === 0;
    const mat = new THREE.MeshStandardMaterial({ color: red ? 0xdc2626 : 0x16a34a, emissive: red ? 0xdc2626 : 0x16a34a, emissiveIntensity: 0.3 });
    const m = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.1, 10), mat);
    m.position.set(-110 + i * 11.5, 0.35, red ? -28.6 : -18.4);
    scene.add(m);
    buoys.push({ m, mat, k: i });
    disposables.push(m.geometry, mat);
  }

  // Trees on the green bank and margins.
  const N = 90;
  const trees = new THREE.InstancedMesh(new THREE.ConeGeometry(1.5, 4.2, 6), new THREE.MeshStandardMaterial({ roughness: 1, flatShading: true }), N);
  const tmp = new THREE.Object3D();
  const col = new THREE.Color();
  for (let i = 0; i < N; i++) {
    const west = i % 3 === 0;
    const x = west ? -95 + ((i * 53) % 55) : -150 + ((i * 89) % 300);
    const z = west ? 24 + ((i * 41) % 70) : -60 + ((i * 29) % 22);
    tmp.position.set(x, 2.2, z);
    const s = 0.7 + ((i * 17) % 10) / 12;
    tmp.scale.set(s, s, s);
    tmp.updateMatrix();
    trees.setMatrixAt(i, tmp.matrix);
    trees.setColorAt(i, col.setHSL(0.31 + ((i * 7) % 8) / 100, 0.42, 0.38 + ((i * 5) % 6) / 40));
  }
  scene.add(trees);
  disposables.push(trees.geometry, trees.material as THREE.Material);

  // Road with trucks.
  const trucks = Array.from({ length: 5 }, (_, i) => {
    const g = new THREE.Group();
    const cab = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.9, 0.9), new THREE.MeshStandardMaterial({ color: [0xdc2626, 0x0e7490, 0xd97706][i % 3] }));
    const trailer = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.0, 1.0), new THREE.MeshStandardMaterial({ color: 0xe5e7eb }));
    trailer.position.x = -1.9; cab.position.y = trailer.position.y = 0.95;
    const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.18, 8, 8), new THREE.MeshBasicMaterial({ color: 0xfff2b0 }));
    lamp.position.set(0.6, 0.85, 0);
    g.add(cab, trailer, lamp);
    scene.add(g);
    return { g, lane: i % 2, speed: 5 + (i % 3) * 1.5, off: i * 38 };
  });

  // Quay lamps.
  const lampMat = new THREE.MeshBasicMaterial({ color: 0xfff2b0 });
  const lamps: THREE.Mesh[] = [];
  for (let x = -26; x <= 56; x += 9) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 3.2, 6), new THREE.MeshStandardMaterial({ color: 0x475569 }));
    pole.position.set(x, 2, 46.5);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.28, 10, 10), lampMat);
    head.position.set(x, 3.7, 46.5);
    scene.add(pole, head);
    lamps.push(head);
    disposables.push(pole.geometry);
  }
  disposables.push(lampMat);

  let lastHero = new THREE.Vector3();
  let acc = 0;
  const fwd = new THREE.Vector3();

  return {
    /** Sun, sky and fog follow a morning-to-golden-hour arc over the loop. */
    update(u: FxUpdate) {
      const { time, dt, cycle01, hero, heroYaw } = u;
      const a = cycle01 * Math.PI * 0.85 + 0.15;
      const elevation = Math.sin(a);
      sun.position.set(-70 * Math.cos(a), 30 + 80 * elevation, 45);
      const warm = 1 - elevation;
      sun.color.setRGB(1, 0.93 - warm * 0.18, 0.82 - warm * 0.34);
      sun.intensity = 1.5 + elevation * 0.6;
      hemi.intensity = 0.95 + elevation * 0.25;
      skyMat.uniforms.uSunDir.value.set(sun.position.x, sun.position.y - 10, sun.position.z).normalize();
      skyMat.uniforms.uHorizon.value.setRGB(1, 0.96 - warm * 0.16, 0.9 - warm * 0.3);
      skyMat.uniforms.uTop.value.setRGB(0.55 - warm * 0.08, 0.78 - warm * 0.1, 0.94 - warm * 0.1);
      if (scene.fog) (scene.fog as THREE.Fog).color.copy(skyMat.uniforms.uHorizon.value);
      lamps.forEach((l) => l.scale.setScalar(1 + Math.max(0, warm - 0.55) * 1.6));

      clouds.forEach((c, i) => { c.position.x += dt * (1.2 + (i % 4) * 0.5); if (c.position.x > 300) c.position.x = -300; });

      birds.forEach((b) => {
        const ang = time * b.speed + b.phase;
        b.g.position.set(12 + Math.cos(ang) * b.radius, b.h + Math.sin(time * 0.7 + b.phase) * 1.5, -6 + Math.sin(ang) * b.radius * 0.6);
        b.g.rotation.y = -ang + Math.PI / 2;
        const flap = Math.sin(time * 9 + b.phase * 3) * 0.6;
        b.l.rotation.z = flap; b.r.rotation.z = -flap;
      });

      buoys.forEach((b) => { b.mat.emissiveIntensity = 0.25 + (Math.sin(time * 2.4 + b.k * 0.9) > 0.55 ? 0.9 : 0); b.m.position.y = 0.35 + Math.sin(time * 1.3 + b.k) * 0.05; });

      trucks.forEach((tk) => {
        const span = 160;
        const p = ((time * tk.speed + tk.off) % span);
        const x = tk.lane === 0 ? -70 + p : 90 - p;
        tk.g.position.set(x, 0, tk.lane === 0 ? 50 : 51.4);
        tk.g.rotation.y = tk.lane === 0 ? 0 : Math.PI;
      });

      // Hero: wake, bow wave, funnel smoke.
      fwd.set(Math.cos(heroYaw), 0, -Math.sin(heroYaw));
      const speed = hero.position.distanceTo(lastHero) / Math.max(dt, 1e-3);
      lastHero.copy(hero.position);
      acc += dt;
      if (acc > 0.03 && speed > 0.5) {
        acc = 0;
        const side = new THREE.Vector3(-fwd.z, 0, fwd.x);
        for (const sgn of [-1, 1]) {
          foam.spawn(hero.position.x - fwd.x * 11.4 + side.x * sgn * 1.2, 0.14, hero.position.z - fwd.z * 11.4 + side.z * sgn * 1.2, side.x * sgn * 0.6 - fwd.x * 0.4, 0, side.z * sgn * 0.6 - fwd.z * 0.4, 3.2, 0.8, 1.6);
          foam.spawn(hero.position.x + fwd.x * 10.6 + side.x * sgn * 1.4, 0.16, hero.position.z + fwd.z * 10.6 + side.z * sgn * 1.4, side.x * sgn * 1.2, 0, side.z * sgn * 1.2, 1.6, 0.55, 0.9);
        }
      }
      if (Math.random() < dt * 14) {
        const f = new THREE.Vector3(-10.2, 5.4, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), heroYaw).add(hero.position);
        smoke.spawn(f.x, f.y, f.z, 0.5 + Math.random() * 0.3, 1.1 + Math.random() * 0.5, (Math.random() - 0.5) * 0.4, 3.4, 0.5, 2.4);
      }
      // Tug leads the ship on the river, the lock approach and the leaving leg.
      const tugOn = (u.t > 2 && u.t < 22.5) || (u.t > 33.5 && u.t < 45);
      tug.visible = tugOn;
      if (tugOn) {
        const side = new THREE.Vector3(-fwd.z, 0, fwd.x);
        tug.position.set(hero.position.x + fwd.x * 15 + side.x * 1.6, 0.12 + Math.sin(time * 1.6) * 0.03, hero.position.z + fwd.z * 15 + side.z * 1.6);
        tug.rotation.y = heroYaw;
        if (Math.random() < dt * 22) foam.spawn(tug.position.x - fwd.x * 2, 0.14, tug.position.z - fwd.z * 2, -fwd.x * 0.5, 0, -fwd.z * 0.5, 2, 0.6, 1.2);
        if (Math.random() < dt * 6) smoke.spawn(tug.position.x, 1.9, tug.position.z, 0.5, 0.9, 0, 2.2, 0.3, 1.2);
      }
      // Coal dust while grabs work, plus the tall chimney plume.
      if (u.unloading && Math.random() < dt * 40) dust.spawn(-2 + Math.random() * 12, 3.4 + Math.random() * 1.5, 44 + Math.random() * 3, (Math.random() - 0.3) * 0.6, 0.7, 0.4, 2.2, 0.35, 1.6);
      if (Math.random() < dt * 9) plume.spawn(84, 16.5, 36, 0.9, 1.6 + Math.random() * 0.6, 0.3, 6, 0.9, 6);
      foam.update(dt); smoke.update(dt); dust.update(dt); plume.update(dt);
    },
    dispose() { disposables.forEach((d) => d.dispose()); },
  };
}
