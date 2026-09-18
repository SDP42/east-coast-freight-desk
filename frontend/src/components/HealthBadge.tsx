import { useEffect, useState } from "react";
import { getHealth, type HealthStatus } from "../lib/api";

export default function HealthBadge() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      getHealth()
        .then((h) => !cancelled && (setHealth(h), setError(null)))
        .catch(() => !cancelled && setError("Backend unreachable"));
    check();
    const id = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-down/30 bg-down/10 px-3 py-1 text-xs text-down">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-down" /> {error}
      </span>
    );
  }

  if (!health) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-border-soft bg-panel px-3 py-1 text-xs text-muted">
        Checking backend…
      </span>
    );
  }

  const ok = health.status === "ok";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${
        ok ? "border-up/30 bg-up/10 text-up" : "border-amber/30 bg-amber/10 text-amber"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-up" : "bg-amber"} ${ok ? "" : "animate-pulse"}`} />
      API {health.status} · DB {health.database} · cache {health.cache} · {health.latency_ms}ms
    </span>
  );
}
