import axios from "axios";

/**
 * The free Render server sleeps after 15 idle minutes and takes about 30 seconds to wake. Instead of letting every page
 * fire requests that time out, the app pings a light health route first, shows one calm banner, and only then lets
 * the real requests through. Requests that still fail with a transient error are retried after another wake check.
 */
export type WakeState = "unknown" | "waking" | "ready";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const MAX_WAIT_MS = 120_000;
const STALE_AFTER_MS = 8 * 60_000; // the server may have gone back to sleep if we have not heard from it for a while

let state: WakeState = "unknown";
let startedAt = 0;
let lastOk = 0;
let pending: Promise<void> | null = null;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const getWake = () => ({ state, startedAt });
export function subscribeWake(fn: () => void) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

async function poll(): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < MAX_WAIT_MS) {
    try {
      await axios.get(`${BASE}/healthz`, { timeout: 10_000 });
      lastOk = Date.now();
      state = "ready";
      emit();
      return;
    } catch {
      await sleep(2500);
    }
  }
  state = "ready"; // stop waiting; the real requests will now show a genuine error if the server is down
  emit();
}

/** Resolves when the backend answers. Cheap when it is already known to be awake. */
export function ensureAwake(): Promise<void> {
  if (state === "ready" && Date.now() - lastOk > STALE_AFTER_MS) state = "unknown";
  if (state === "ready") return Promise.resolve();
  if (!pending) {
    state = "waking";
    startedAt = Date.now();
    emit();
    pending = poll().finally(() => { pending = null; });
  }
  return pending;
}

export function noteOk() { lastOk = Date.now(); }
export function markMaybeAsleep() { if (state === "ready") { state = "unknown"; emit(); } }
