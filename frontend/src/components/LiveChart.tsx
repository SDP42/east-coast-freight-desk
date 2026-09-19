import { useEffect, useMemo, useState } from "react";
import { px } from "../lib/scale";
import { Area, AreaChart, CartesianGrid, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Pause, Play, TrendingDown, TrendingUp } from "lucide-react";
import { getHistory, type HistoryPoint } from "../lib/api";

interface LiveChartProps {
  indexName: string;
  label?: string;
  height?: number;
  compact?: boolean;
}

const WINDOW = 120;
const BASE_TICK_MS = 700;
const SPEEDS = [1, 3, 8];

/** Streams a real historical series onto the chart one observation at a time,
 * so price spikes and collapses play out visually. This is a replay of real
 * ingested data at accelerated speed, and the UI says so — it is not a live
 * market feed (no free live freight feed exists). A move counts as
 * a spike/drop when its daily change is beyond 2 standard deviations of that
 * series' own daily changes. */
export default function LiveChart({ indexName, label, height = 300, compact = false }: LiveChartProps) {
  const [data, setData] = useState<HistoryPoint[]>([]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData([]);
    setError(false);
    getHistory(indexName, 700)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setCursor(Math.min(WINDOW, d.length - 1));
      })
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, [indexName]);

  useEffect(() => {
    if (!playing || data.length < 2) return;
    const id = setInterval(() => {
      setCursor((c) => (c + 1 >= data.length ? Math.min(WINDOW, data.length - 1) : c + 1));
    }, BASE_TICK_MS / speed);
    return () => clearInterval(id);
  }, [playing, speed, data.length]);

  const threshold = useMemo(() => {
    if (data.length < 3) return Infinity;
    const changes = data.slice(1).map((p, i) => (p.value - data[i].value) / data[i].value);
    const mean = changes.reduce((a, b) => a + b, 0) / changes.length;
    const sd = Math.sqrt(changes.reduce((a, b) => a + (b - mean) ** 2, 0) / changes.length);
    return 2 * sd;
  }, [data]);

  const visible = useMemo(() => {
    const start = Math.max(0, cursor - WINDOW + 1);
    return data.slice(start, cursor + 1).map((p, i, arr) => {
      const prev = i > 0 ? arr[i - 1].value : p.value;
      const change = prev ? (p.value - prev) / prev : 0;
      return { ...p, change, event: Math.abs(change) > threshold ? (change > 0 ? "spike" : "drop") : null };
    });
  }, [data, cursor, threshold]);

  if (error) return <p className="text-sm text-down">Could not load {indexName} history — is the backend running?</p>;
  if (visible.length < 2) return <div className="flex items-center justify-center text-sm text-muted" style={{ height: px(height) }}>Loading {indexName}…</div>;

  const last = visible[visible.length - 1];
  const first = visible[0];
  const prev = visible[visible.length - 2];
  const tickUp = last.value >= prev.value;
  const trendUp = last.value >= first.value;
  const color = trendUp ? "#059669" : "#dc2626";
  const events = visible.filter((p) => p.event);
  const biggest = events.length ? events.reduce((a, b) => (Math.abs(b.change) > Math.abs(a.change) ? b : a)) : null;
  const gradId = `grad-${indexName}`;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">{label ?? indexName}</p>
          <div className="flex items-baseline gap-3">
            <span key={cursor} className={`rounded px-1 text-3xl font-bold tabular-nums text-strong ${tickUp ? "flash-up" : "flash-down"}`}>
              {last.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
            <span className={`flex items-center gap-1 text-sm font-semibold tabular-nums ${tickUp ? "text-up" : "text-down"}`}>
              {tickUp ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              {(last.change * 100 >= 0 ? "+" : "") + (last.change * 100).toFixed(2)}%
            </span>
          </div>
          <p className="text-[11px] text-muted">
            {last.date} · replaying real history
          </p>
        </div>

        {!compact && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPlaying((p) => !p)}
              className="flex h-8 w-8 items-center justify-center rounded-md border border-border-soft bg-panel-light text-strong hover:border-cyan/40"
              aria-label={playing ? "Pause" : "Play"}
            >
              {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            </button>
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`h-8 rounded-md border px-2.5 text-xs ${speed === s ? "border-cyan/50 bg-cyan/10 text-cyan" : "border-border-soft bg-panel-light text-muted hover:text-strong"}`}
              >
                {s}x
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3">
        <ResponsiveContainer width="100%" height={px(height)}>
          <AreaChart data={visible} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            {!compact && <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />}
            <XAxis dataKey="date" hide={compact} tick={{ fontSize: px(10), fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#dbe4ee" }} minTickGap={40} />
            <YAxis hide={compact} domain={[(min: number) => min * 0.97, (max: number) => max * 1.03]} tick={{ fontSize: px(10), fill: "#64748b" }} tickLine={false} axisLine={false} width={48} tickFormatter={(v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 0 })} />
            {!compact && <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #dbe4ee", borderRadius: 8, fontSize: px(12) }} labelStyle={{ color: "#64748b" }} />}
            <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill={`url(#${gradId})`} isAnimationActive={false} />
            {events.map((e) => (
              <ReferenceDot key={e.date} x={e.date} y={e.value} r={5} fill={e.event === "spike" ? "#059669" : "#dc2626"} stroke="#f3f7fb" strokeWidth={2} />
            ))}
            <ReferenceDot x={last.date} y={last.value} r={4} fill={color} stroke="#fff" strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {!compact && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted">
          <span>
            {biggest
              ? `Largest ${biggest.event} in view: ${(biggest.change * 100).toFixed(1)}% on ${biggest.date}`
              : "No statistically unusual move in view"}
          </span>
          <span className="flex items-center gap-3">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-up" /> spike</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-down" /> drop</span>
            <span>(move beyond 2σ of this series' daily changes)</span>
          </span>
        </div>
      )}
    </div>
  );
}
