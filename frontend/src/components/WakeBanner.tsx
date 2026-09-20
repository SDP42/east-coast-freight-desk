import { useEffect, useState } from "react";
import { getWake, subscribeWake } from "../lib/wake";

/** One calm message while the free server wakes up, instead of a page full of errors. */
export default function WakeBanner() {
  const [, force] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [flash, setFlash] = useState(false);

  useEffect(() => subscribeWake(() => force((n) => n + 1)), []);
  const { state, startedAt } = getWake();
  const waking = state === "waking";
  const elapsed = waking ? Math.round((now - startedAt) / 1000) : 0;

  useEffect(() => {
    if (!waking) return;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [waking]);

  useEffect(() => {
    if (state === "ready" && startedAt && Date.now() - startedAt > 3000) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 2200);
      return () => clearTimeout(t);
    }
  }, [state, startedAt]);

  if (waking && elapsed >= 2) {
    const pct = Math.min(96, Math.round((elapsed / 40) * 100));
    return (
      <div role="status" className="fixed left-1/2 top-3 z-[90] w-[min(92vw,34rem)] -translate-x-1/2 rounded-2xl border border-border-soft bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-strong">Waking the server… {elapsed}s</p>
            <p className="text-xs text-muted">The free host sleeps when idle and takes about 30 seconds the first time. Everything loads automatically once it is ready.</p>
          </div>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-teal-500 transition-all duration-500" style={{ width: `${pct}%` }} /></div>
      </div>
    );
  }
  if (flash) {
    return <div role="status" className="fixed left-1/2 top-3 z-[90] -translate-x-1/2 rounded-full border border-up/30 bg-white/95 px-4 py-2 text-sm font-semibold text-up shadow-lg">Server ready ✓</div>;
  }
  return null;
}
