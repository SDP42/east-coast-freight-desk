import { lazy, Suspense, useEffect, useState } from "react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { Globe2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import type { Chokepoint } from "../components/three/GlobeScene";

const GlobeScene = lazy(() => import("../components/three/GlobeScene"));
interface Cp extends Chokepoint { why: string; weekly: number[]; through: string }
interface Data { chokepoints: Cp[]; lanes: Record<string, number[][]>; note: string | null; method: string }
const COLORS: Record<string, string> = { Australia: "#0e7490", Indonesia: "#059669", Mozambique: "#d97706", Russia: "#7c3aed", "United States (Suez)": "#dc2626", "United States (Cape)": "#f97316" };
const tone = (r: number | null) => (r === null ? "text-muted" : r < 0.75 ? "text-down" : r < 0.95 ? "text-amber" : r > 1.2 ? "text-cyan" : "text-up");

export default function TradeGlobe() {
  const [data, setData] = useState<Data | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => { api.get<Data>("/lab/chokepoints").then((r) => { setData(r.data); setSel(r.data.chokepoints[0]?.name ?? null); }); }, []);
  const cur = data?.chokepoints.find((c) => c.name === sel);
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Trade globe" subtitle="Where the coal sails and where the chokepoints are running hot or cold. Drag to rotate, scroll to zoom, click a marker for its traffic." />
      <div className="grid gap-4 lg:grid-cols-3">
        <SpotlightCard className="lg:col-span-2">
          <div className="relative h-[34rem] bg-gradient-to-b from-sky-50 to-white">
            {data ? (
              <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-muted">Loading the globe…</div>}>
                <GlobeScene className="h-full" chokepoints={data.chokepoints} lanes={data.lanes} selected={sel} onSelect={setSel} />
              </Suspense>
            ) : <div className="flex h-full items-center justify-center text-sm text-muted">Reading chokepoint traffic…</div>}
            <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 rounded-xl border border-border-soft bg-white/90 px-3 py-2 text-[10px] backdrop-blur">
              {Object.entries(COLORS).map(([k, c]) => <span key={k} className="flex items-center gap-1 text-body"><span className="h-1.5 w-3 rounded-full" style={{ background: c }} />{k}</span>)}
            </div>
          </div>
        </SpotlightCard>
        <div className="space-y-4">
          {cur && (
            <SpotlightCard>
              <div className="p-5">
                <p className="flex items-center gap-2 text-sm font-semibold text-strong"><Globe2 className="h-4 w-4 text-cyan" /> {cur.name}</p>
                <p className="mt-1 text-xs text-muted">{cur.why}</p>
                <div className="mt-3 flex items-end gap-4">
                  <div><p className={`text-3xl font-bold ${tone(cur.ratio)}`}>{cur.ratio !== null ? `${Math.round(cur.ratio * 100)}%` : "n/a"}</p><p className="text-[11px] text-muted">of the pre-Oct-2023 level</p></div>
                  <div className="text-xs text-body"><p>{cur.recent_per_day} dry-bulk ships/day now</p><p className="text-muted">{cur.baseline_per_day}/day before</p></div>
                </div>
                <div className="mt-3 h-16"><ResponsiveContainer><AreaChart data={cur.weekly.map((v, i) => ({ i, v }))}><Area dataKey="v" stroke="#0e7490" fill="#0e7490" fillOpacity={0.15} strokeWidth={1.5} isAnimationActive={false} /></AreaChart></ResponsiveContainer></div>
                <p className="text-[10px] text-muted">Weekly mean, last 52 weeks, through {cur.through}</p>
              </div>
            </SpotlightCard>
          )}
          <SpotlightCard>
            <div className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Chokepoints, coldest first</p>
              <ul className="mt-2 space-y-1">
                {data?.chokepoints.map((c) => (
                  <li key={c.name}><button onClick={() => setSel(c.name)} className={`flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-sm transition hover:bg-panel-light ${c.name === sel ? "bg-panel-light" : ""}`}>
                    <span className="text-body">{c.name}</span><span className={`font-semibold ${tone(c.ratio)}`}>{c.ratio !== null ? `${Math.round(c.ratio * 100)}%` : "n/a"}</span></button></li>
                ))}
              </ul>
            </div>
          </SpotlightCard>
        </div>
      </div>
      {data?.note && <div className="mt-4"><Note kind="warn">{data.note}</Note></div>}
      {data && <p className="mt-3 text-[11px] text-muted">{data.method} Lane routes are hand-placed for illustration; ships on the lanes are decorative. Land outlines: Natural Earth (public domain).</p>}
    </div>
  );
}
