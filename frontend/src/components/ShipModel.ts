import * as THREE from "three";

/**
 * A dry-bulk carrier built the way a naval architect draws one: the hull is lofted from cross-sections (flat bottom,
 * rounded bilge, flared bow with a raked stem, sheer line, transom stern), painted in the usual three bands
 * (red anti-fouling, dark boot-top, topsides), with hatch covers and coamings, geared deck cranes, a multi-deck
 * accommodation block with window strips, bridge wings, a funnel with a company band, radar mast and bulbous bow.
 * Length runs along +X (bow at +X); waterline is y = 0; starboard is +Z.
 */

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

interface Dims { L: number; B: number; D: number; F: number }

/** Half-beam factor along the length (0 stern .. 1 bow). */
function beamFactor(t: number): number {
  if (t < 0.16) return 0.7 + 0.3 * smooth(0, 0.16, t); // stern run-in to the transom
  if (t < 0.7) return 1;
  const k = (t - 0.7) / 0.3;
  return Math.max(0, Math.pow(1 - Math.pow(k, 2.1), 0.62)); // bow entrance
}

function keelDepth(t: number, D: number): number {
  const stern = 0.8 + 0.2 * smooth(0, 0.12, t); // skeg rise aft
  const bow = t > 0.78 ? 1 - 0.42 * Math.pow((t - 0.78) / 0.22, 2) : 1; // forefoot
  return D * stern * bow;
}

function deckHeight(t: number, F: number): number {
  const bow = t > 0.82 ? 0.55 * F * Math.pow((t - 0.82) / 0.18, 2) : 0; // sheer up at the bow
  const stern = t < 0.08 ? 0.12 * F * (1 - t / 0.08) : 0;
  return F + bow + stern;
}

function hullGeometry(d: Dims, hull: THREE.Color): { side: THREE.BufferGeometry; deck: THREE.BufferGeometry } {
  const N = 72, M = 12;
  const red = new THREE.Color(0x7a1c1c), band = new THREE.Color(0x141a22), top = hull;
  const pos: number[] = [], col: number[] = [], idx: number[] = [];
  const loop = 2 * (M + 1); // port deck -> keel, then keel -> starboard deck
  const at = (i: number, j: number) => i * loop + j;
  const tmp = new THREE.Color();
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const x = (t - 0.5) * d.L;
    const bw = beamFactor(t) * (d.B / 2);
    const dk = keelDepth(t, d.D), dh = deckHeight(t, d.F);
    for (let j = 0; j < loop; j++) {
      const port = j <= M;
      const u = port ? 1 - j / M : (j - (M + 1)) / M; // 1 at the deck, 0 at the keel
      const bilge = 0.24;
      const round = u < bilge ? Math.sqrt(Math.max(0, 1 - Math.pow((bilge - u) / bilge, 2))) : 1;
      const flare = 1 + 0.16 * u * smooth(0.55, 1, t);
      const w = bw * (0.55 + 0.45 * round) * flare;
      const rake = u * (1 - u * 0.2) * 0.9 * smooth(0.86, 1, t) * d.L * 0.035; // raked stem
      const y = -dk + u * (dk + dh);
      pos.push(x + rake, y, port ? -w : w);
      if (y < 0.0) tmp.copy(red); else if (y < 0.16 * d.B / 3.3) tmp.copy(band); else tmp.copy(top);
      col.push(tmp.r, tmp.g, tmp.b);
    }
  }
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < loop - 1; j++) idx.push(at(i, j), at(i + 1, j), at(i, j + 1), at(i, j + 1), at(i + 1, j), at(i + 1, j + 1));
  }
  // Transom: plate between the port and starboard sides at the stern.
  for (let k = 0; k < M; k++) {
    const a = at(0, k), b = at(0, k + 1), c = at(0, loop - 1 - k), e = at(0, loop - 2 - k);
    idx.push(a, b, c, b, e, c);
  }
  const side = new THREE.BufferGeometry();
  side.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  side.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  side.setIndex(idx);
  side.computeVertexNormals();

  const dp: number[] = [], di: number[] = [];
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const x = (t - 0.5) * d.L, bw = beamFactor(t) * (d.B / 2) * (1 + 0.16 * smooth(0.55, 1, t)), y = deckHeight(t, d.F);
    const rake = 0.9 * 0.8 * smooth(0.86, 1, t) * d.L * 0.035;
    dp.push(x + rake, y, -bw, x + rake, y, bw);
  }
  for (let i = 0; i < N; i++) { const a = i * 2; di.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  const deck = new THREE.BufferGeometry();
  deck.setAttribute("position", new THREE.Float32BufferAttribute(dp, 3));
  deck.setIndex(di);
  deck.computeVertexNormals();
  return { side, deck };
}

const std = (color: number, rough = 0.6, metal = 0.05) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });

export function makeBulker(hullColor: number, scale = 1): THREE.Group {
  const g = new THREE.Group();
  const d: Dims = { L: 22.9 * scale, B: 3.4 * scale, D: 0.95 * scale, F: 0.82 * scale };
  const s = scale;
  const { side, deck } = hullGeometry(d, new THREE.Color(hullColor));
  const hullMesh = new THREE.Mesh(side, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.5, metalness: 0.2, side: THREE.DoubleSide }));
  hullMesh.castShadow = true;
  hullMesh.receiveShadow = true;
  g.add(hullMesh);
  const deckMesh = new THREE.Mesh(deck, new THREE.MeshStandardMaterial({ color: 0x5f6e64, roughness: 0.85, side: THREE.DoubleSide }));
  deckMesh.receiveShadow = true;
  g.add(deckMesh);

  const y0 = d.F; // main deck height
  const white = std(0xf1f3f5, 0.55), steel = std(0x8b95a1, 0.5, 0.3), dark = std(0x0e141b, 0.3, 0.6);
  const bulbous = new THREE.Mesh(new THREE.SphereGeometry(0.42 * s, 14, 10), new THREE.MeshStandardMaterial({ color: 0x7a1c1c, roughness: 0.5 }));
  bulbous.scale.set(1.9, 0.75, 0.8);
  bulbous.position.set(d.L / 2 - 0.15 * s, -d.D * 0.62, 0);
  g.add(bulbous);

  // Seven cargo holds: coamings, hatch covers and their ribs, between the accommodation block and the forecastle.
  const holdStart = -d.L * 0.24, holdEnd = d.L * 0.34, n = 7;
  const step = (holdEnd - holdStart) / n;
  const coaming = std(0x9aa3ad, 0.55, 0.2), cover = std(0x6f7c89, 0.5, 0.25);
  for (let i = 0; i < n; i++) {
    const cx = holdStart + step * (i + 0.5);
    const hw = d.B * 0.54, hl = step * 0.82;
    const frame = new THREE.Mesh(new THREE.BoxGeometry(hl, 0.16 * s, hw), coaming);
    frame.position.set(cx, y0 + 0.08 * s, 0);
    const lid = new THREE.Mesh(new THREE.BoxGeometry(hl * 0.94, 0.05 * s, hw * 0.92), cover);
    lid.position.set(cx, y0 + 0.19 * s, 0);
    lid.castShadow = true;
    g.add(frame, lid);
    for (let r = -1; r <= 1; r++) {
      const rib = new THREE.Mesh(new THREE.BoxGeometry(hl * 0.9, 0.03 * s, 0.03 * s), coaming);
      rib.position.set(cx, y0 + 0.23 * s, r * hw * 0.28);
      g.add(rib);
    }
    if (i % 2 === 1 && i < n - 1) { // geared crane between holds, on the centreline
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * s, 0.13 * s, 0.7 * s, 10), white);
      ped.position.set(cx + step / 2, y0 + 0.35 * s, 0);
      const cab = new THREE.Mesh(new THREE.BoxGeometry(0.22 * s, 0.2 * s, 0.2 * s), white);
      cab.position.set(cx + step / 2, y0 + 0.78 * s, 0.1 * s);
      const boom = new THREE.Mesh(new THREE.CylinderGeometry(0.03 * s, 0.05 * s, 2.4 * s, 8), std(0xd6a418, 0.5, 0.2));
      boom.rotation.z = Math.PI / 2 - 0.16;
      boom.position.set(cx + step / 2 + 1.1 * s, y0 + 0.9 * s, 0);
      boom.castShadow = true;
      g.add(ped, cab, boom);
    }
  }

  // Accommodation block: four decks with window strips, bridge with wings, funnel, radar mast.
  const hx = -d.L * 0.385, hb = d.B * 0.78;
  const decks = [[2.0, 1.3], [1.75, 1.25], [1.5, 1.2], [1.28, 1.1]];
  let yy = y0;
  decks.forEach(([len, wid], i) => {
    const h = 0.42 * s;
    const blk = new THREE.Mesh(new THREE.BoxGeometry(len * s * 0.8, h, hb * (wid / 1.3) * 0.95), white);
    blk.position.set(hx + (i === 0 ? 0 : 0.05 * s), yy + h / 2, 0);
    blk.castShadow = true;
    g.add(blk);
    const win = new THREE.Mesh(new THREE.BoxGeometry(len * s * 0.805, 0.1 * s, hb * (wid / 1.3) * 0.955), dark);
    win.position.copy(blk.position).setY(yy + h * 0.62);
    g.add(win);
    yy += h;
  });
  const wings = new THREE.Mesh(new THREE.BoxGeometry(0.5 * s, 0.06 * s, d.B * 1.02), white);
  wings.position.set(hx + 0.2 * s, yy - 0.12 * s, 0);
  g.add(wings);
  const funnel = new THREE.Mesh(new THREE.CylinderGeometry(0.2 * s, 0.26 * s, 0.75 * s, 14), std(0x1b2a41, 0.5));
  funnel.position.set(hx - 0.55 * s, y0 + 1.45 * s, 0);
  const funnelBand = new THREE.Mesh(new THREE.CylinderGeometry(0.212 * s, 0.24 * s, 0.14 * s, 14), std(0xd97706, 0.5));
  funnelBand.position.set(hx - 0.55 * s, y0 + 1.5 * s, 0);
  const funnelTop = new THREE.Mesh(new THREE.CylinderGeometry(0.2 * s, 0.2 * s, 0.1 * s, 14), std(0x0a0d12, 0.9));
  funnelTop.position.set(hx - 0.55 * s, y0 + 1.86 * s, 0);
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.02 * s, 0.03 * s, 0.9 * s, 6), steel);
  mast.position.set(hx + 0.25 * s, yy + 0.45 * s, 0);
  const radar = new THREE.Mesh(new THREE.BoxGeometry(0.02 * s, 0.05 * s, 0.5 * s), steel);
  radar.position.set(hx + 0.25 * s, yy + 0.9 * s, 0);
  g.add(funnel, funnelBand, funnelTop, mast, radar);

  // Forecastle: windlass, anchor, mooring bollards and a foremast.
  const fore = new THREE.Mesh(new THREE.BoxGeometry(1.0 * s, 0.2 * s, d.B * 0.55), steel);
  fore.position.set(d.L * 0.43, deckHeight(0.93, d.F) + 0.1 * s, 0);
  const wind = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * s, 0.1 * s, 0.32 * s, 10), std(0x2b3542, 0.5, 0.4));
  wind.rotation.x = Math.PI / 2;
  wind.position.set(d.L * 0.43, deckHeight(0.93, d.F) + 0.3 * s, 0);
  const foremast = new THREE.Mesh(new THREE.CylinderGeometry(0.015 * s, 0.025 * s, 0.8 * s, 6), steel);
  foremast.position.set(d.L * 0.45, deckHeight(0.95, d.F) + 0.5 * s, 0);
  g.add(fore, wind, foremast);
  // Rails along both sides of the main deck.
  for (const zs of [-1, 1]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(d.L * 0.68, 0.025 * s, 0.025 * s), steel);
    rail.position.set(-d.L * 0.02, y0 + 0.22 * s, zs * d.B * 0.49);
    g.add(rail);
  }
  // Navigation lights (starboard is +Z).
  const green = new THREE.Mesh(new THREE.SphereGeometry(0.06 * s, 8, 8), new THREE.MeshBasicMaterial({ color: 0x22c55e }));
  green.position.set(hx + 0.25 * s, yy - 0.1 * s, d.B * 0.52);
  const redL = new THREE.Mesh(new THREE.SphereGeometry(0.06 * s, 8, 8), new THREE.MeshBasicMaterial({ color: 0xef4444 }));
  redL.position.set(hx + 0.25 * s, yy - 0.1 * s, -d.B * 0.52);
  g.add(green, redL);
  return g;
}
