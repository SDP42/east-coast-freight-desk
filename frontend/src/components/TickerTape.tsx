import { useEffect, useRef, useState } from "react";
import { getTicker, type TickerItem } from "../lib/api";

const POLL_INTERVAL_MS = 60_000;

function Tick({ item, justChanged }: { item: TickerItem; justChanged: boolean }) {
  const up = (item.change ?? 0) > 0;
  const down = (item.change ?? 0) < 0;
  return (
    <div
      className={`flex items-center gap-2 px-5 py-2 border-r border-white/5 whitespace-nowrap ${
        justChanged ? (up ? "flash-up" : down ? "flash-down" : "") : ""
      }`}
      title={`As of ${item.date}${item.prev_date ? ` (prev: ${item.prev_date})` : ""} — real ingested data, not a live streaming feed`}
    >
      <span className="text-xs font-semibold text-muted tracking-wide">{item.index_name}</span>
      <span className="text-sm font-semibold text-white tabular-nums">
        {item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </span>
      {item.change !== null && item.change !== 0 && (
        <span className={`text-xs tabular-nums ${up ? "text-up" : "text-down"}`}>
          {up ? "▲" : "▼"} {Math.abs(item.change_pct ?? 0).toFixed(2)}%
        </span>
      )}
      <span className="text-[10px] text-muted uppercase hidden sm:inline">{item.label}</span>
      <span className="text-[10px] text-muted/60 hidden lg:inline">as of {item.date}</span>
    </div>
  );
}

export default function TickerTape() {
  const [items, setItems] = useState<TickerItem[]>([]);
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [error, setError] = useState(false);
  const prevValues = useRef<Record<string, number> | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchTicker = () => {
      getTicker()
        .then((data) => {
          if (cancelled) return;
          const prev = prevValues.current;
          if (prev) {
            const changed = new Set(data.filter((d) => prev[d.index_name] !== undefined && prev[d.index_name] !== d.value).map((d) => d.index_name));
            setChangedKeys(changed);
          }
          prevValues.current = Object.fromEntries(data.map((d) => [d.index_name, d.value]));
          setItems(data);
          setError(false);
        })
        .catch(() => !cancelled && setError(true));
    };

    fetchTicker();
    const id = setInterval(fetchTicker, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error) {
    return (
      <div className="w-full border-b border-white/5 bg-black/40 px-5 py-2 text-xs text-down">
        Live market data unavailable — is the backend running?
      </div>
    );
  }

  if (items.length === 0) {
    return <div className="w-full border-b border-white/5 bg-black/40 px-5 py-2 text-xs text-muted">Loading market data…</div>;
  }

  const track = [...items, ...items];

  return (
    <div className="relative w-full overflow-hidden border-b border-white/5 bg-black/40 backdrop-blur">
      <div className="flex w-max animate-marquee">
        {track.map((item, i) => (
          <Tick key={`${item.index_name}-${i}`} item={item} justChanged={changedKeys.has(item.index_name)} />
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-navy to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-navy to-transparent" />
    </div>
  );
}
