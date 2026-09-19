import { useEffect, useMemo, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Pause, Play, Zap } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Sparkline from "../components/Sparkline";
import { Note, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { px } from "../lib/scale";

interface Seed { key: string; label: string; unit: string; prev_close: number; last_close: number; prev_date: string; last_date: string; daily_vol: number }
interface State { x: number; t: number; ticks: number[]; flash: "up" | "down" | ""; open: number }
const DAY_MINUTES = 390;

const gauss = () => { let u = 0, v = 0; while (u === 0) u = Math.random(); while (v === 0) v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };

/** One Brownian-bridge step in log space: drifts from the previous close to the last close over a 390-minute day. */
function step(s: State, seed: Seed): State {
  const a = Math.log(seed.prev_close), b = Math.log(seed.last_close);
  const t = s.t;
  const left = DAY_MINUTES - t;
  const sigma = seed.daily_vol / Math.sqrt(DAY_MINUTES);
  let x = s.x;
  if (left <= 1) x = b;
  else x = x + (b - x) / left + sigma * Math.sqrt((left - 1) / left) * gauss();
  const next = { x, t: left <= 1 ? 0 : t + 1 };
  const price = Math.exp(next.x);
  const prevPrice = Math.exp(s.x);
  const ticks = [...s.ticks, price].slice(-240);
  return { ...next, ticks, flash: price > prevPrice ? "up" : price < prevPrice ? "down" : "", open: left <= 1 ? Math.exp(a) : s.open };
}

export default function LiveDesk() {
  const [seeds, setSeeds] = useState<Seed[]>([]);
  const [note, setNote] = useState("");
  const [state, setState] = useState<Record<string, State>>({});
  const [running, setRunning] = useState(true);
  const [rate, setRate] = useState(4);
  const [sel, setSel] = useState("BPI");
  const seedsRef = useRef<Seed[]>([]);
  const tape = useRef<{ key: string; price: number; t: string; up: boolean }[]>([]);

  useEffect(() => {
    api.get<{ series: Seed[]; note: string }>("/live/seed").then((r) => {
      setSeeds(r.data.series); seedsRef.current = r.data.series; setNote(r.data.note);
      setState(Object.fromEntries(r.data.series.map((s) => [s.key, { x: Math.log(s.prev_close), t: 0, ticks: [s.prev_close], flash: "" as const, open: s.prev_close }])));
    });
  }, []);

  useEffect(() => {
    if (!running || seeds.length === 0) return;
    const id = setInterval(() => {
      setState((prev) => {
        const next: Record<string, State> = {};
        seedsRef.current.forEach((sd) => {
          const st = prev[sd.key];
          if (!st) return;
          if (Math.random() < 0.65 || st.ticks.length < 3) {
            const n = step(st, sd);
            next[sd.key] = n;
            tape.current = [{ key: sd.key, price: n.ticks[n.ticks.length - 1], t: new Date().toLocaleTimeString(), up: n.flash === "up" }, ...tape.current].slice(0, 14);
          } else next[sd.key] = { ...st, flash: "" };
        });
        return next;
      });
    }, Math.round(1000 / rate));
    return () => clearInterval(id);
  }, [running, rate, seeds.length]);

  const cur = useMemo(() => seeds.find((s) => s.key === sel), [seeds, sel]);
  const cs = state[sel];
  const chart = cs ? cs.ticks.map((v, i) => ({ i, v })) : [];
  const fmt = (v: number, unit: string) => (unit === "inr" || unit === "usd/t" ? v.toFixed(2) : v.toLocaleString(undefined, { maximumFractionDigits: 1 }));

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Live desk" subtitle="A trading-desk view with minute-by-minute motion. The ticks are simulated from each series' last real trading day, and the page says so." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className="flex items-center gap-1.5 rounded-full bg-amber/10 px-3 py-1 text-xs font-semibold text-amber"><Zap className="h-3.5 w-3.5" /> SIMULATED TICKS</span>
        <button onClick={() => setRunning((r) => !r)} className="flex items-center gap-1.5 rounded-lg border border-border-soft bg-white px-3 py-1.5 text-xs text-strong hover:border-cyan">{running ? <><Pause className="h-3.5 w-3.5" /> Pause</> : <><Play className="h-3.5 w-3.5" /> Resume</>}</button>
        <label className="flex items-center gap-2 text-xs text-body">Speed <input type="range" min={1} max={20} value={rate} onChange={(e) => setRate(Number(e.target.value))} className="w-32 accent-cyan" /> {rate} ticks/s</label>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {seeds.map((sd) => {
          const st = state[sd.key];
          const price = st ? st.ticks[st.ticks.length - 1] : sd.prev_close;
          const chg = ((price / sd.prev_close) - 1) * 100;
          return (
            <button key={sd.key} onClick={() => setSel(sd.key)} className={`text-left ${sel === sd.key ? "" : "opacity-95"}`}>
              <SpotlightCard className={sel === sd.key ? "ring-2 ring-cyan/40" : ""}>
                <div className={`p-4 transition-colors duration-500 ${st?.flash === "up" ? "flash-up" : st?.flash === "down" ? "flash-down" : ""}`}>
                  <div className="flex items-center justify-between"><p className="text-[11px] font-semibold uppercase tracking-wider text-muted">{sd.key}</p><p className={`text-[11px] font-semibold ${chg >= 0 ? "text-up" : "text-down"}`}>{chg >= 0 ? "▲" : "▼"} {Math.abs(chg).toFixed(2)}%</p></div>
                  <p className="mt-1 text-xl font-bold tabular-nums text-strong">{fmt(price, sd.unit)}</p>
                  <p className="truncate text-[10px] text-muted">{sd.label}</p>
                  <div className="mt-1">{st && st.ticks.length > 2 && <Sparkline values={st.ticks.slice(-60)} up={chg >= 0} width={px(120)} height={px(26)} />}</div>
                </div>
              </SpotlightCard>
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <SpotlightCard className="lg:col-span-2">
          <div className="p-5">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-semibold text-strong">{cur?.label} · last 240 ticks</p>
              {cur && cs && <p className="text-xs text-muted">real anchors: {cur.prev_date} close {fmt(cur.prev_close, cur.unit)} → {cur.last_date} close {fmt(cur.last_close, cur.unit)}</p>}
            </div>
            <div className="mt-2">
              <ResponsiveContainer width="100%" height={px(300)}>
                <LineChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="i" hide />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: px(11), fill: "#64748b" }} width={px(56)} tickFormatter={(v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 })} />
                  <Line dataKey="v" stroke="#0e7490" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </SpotlightCard>
        <SpotlightCard>
          <div className="p-5">
            <p className="text-sm font-semibold text-strong">Tape</p>
            <ul className="mt-2 space-y-1 font-mono text-xs">
              {tape.current.map((t, i) => (
                <li key={i} className={`flex justify-between rounded px-2 py-1 ${t.up ? "text-up" : "text-down"} ${i === 0 ? "bg-panel-light" : ""}`}><span>{t.t}</span><span className="text-strong">{t.key}</span><span>{t.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></li>
              ))}
            </ul>
          </div>
        </SpotlightCard>
      </div>
      <div className="mt-4"><Note kind="warn">{note} The freight indices' last real closes are from July 2019; coal, INR, S&P 500 and the dollar index use their most recent real closes. To connect real minute data for oil, currency or equities, a provider and key would be added behind the same page.</Note></div>
    </div>
  );
}
