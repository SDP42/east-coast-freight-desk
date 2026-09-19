import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export interface Stage {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  onFrame: (cb: (t: number, dt: number) => void) => void;
  dispose: () => void;
}

/** Shared three.js boilerplate: renderer, resize handling, orbit controls, a frame loop and full disposal. */
export function createStage(host: HTMLElement, opts: { fov?: number; position: [number, number, number]; autoRotate?: number; minDistance?: number; maxDistance?: number; background?: number | null }): Stage {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);
  renderer.domElement.style.display = "block";
  const scene = new THREE.Scene();
  if (opts.background !== null && opts.background !== undefined) scene.background = new THREE.Color(opts.background);
  const camera = new THREE.PerspectiveCamera(opts.fov ?? 40, 1, 0.1, 2000);
  camera.position.set(...opts.position);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.autoRotate = !reduced && !!opts.autoRotate;
  controls.autoRotateSpeed = opts.autoRotate ?? 0;
  if (opts.minDistance) controls.minDistance = opts.minDistance;
  if (opts.maxDistance) controls.maxDistance = opts.maxDistance;

  const callbacks: ((t: number, dt: number) => void)[] = [];
  const resize = () => {
    const w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    camera.aspect = w / Math.max(1, h);
    camera.updateProjectionMatrix();
  };
  resize();
  const ro = new ResizeObserver(resize);
  ro.observe(host);

  const clock = new THREE.Clock();
  let raf = 0;
  const loop = () => {
    const dt = clock.getDelta();
    const t = clock.elapsedTime;
    controls.update();
    callbacks.forEach((cb) => cb(t, dt));
    renderer.render(scene, camera);
    raf = requestAnimationFrame(loop);
  };
  loop();

  return {
    renderer, scene, camera, controls,
    onFrame: (cb) => callbacks.push(cb),
    dispose: () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.dispose();
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        const mat = m.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
        else mat?.dispose();
      });
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

/** Screen position of a world point, or null if it is behind the camera. */
export function project(v: THREE.Vector3, camera: THREE.Camera, w: number, h: number): { x: number; y: number } | null {
  const p = v.clone().project(camera);
  if (p.z > 1) return null;
  return { x: (p.x * 0.5 + 0.5) * w, y: (-p.y * 0.5 + 0.5) * h };
}
