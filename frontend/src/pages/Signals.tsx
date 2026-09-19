import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Field, Note, PageHeader, Stat, Tabs, btnCls, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";

type Tab = "slots" | "transfer" | "cyclone" | "demand";
const SLOT_COLOR: Record<string, string> = { open: "#059669", moderate: "#d97706", tight: "#dc2626" };
const PORTS = ["Paradip", "Visakhapatnam", "Haldia", "Dhamra", "Gopalpur"];

interface Slots {
  port: string; data_through: string; reference_calls_per_day_p90: number; open_days: string[]; method: string;
  days: { date: string; expected_calls_per_day: number; pressure: number; slot: string }[];
  backtest: { windows: number; chosen_model: string; mae_calls_per_day: number; naive_mae: number; skill_vs_naive_pct: number | null; mae_by_model: Record<string, number> };
}
function SlotsTool() {
  const [port, setPort] = useState("Paradip");
  const [res, setRes] = useState<Slots | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function run(p: string) {
    setBusy(true); setErr("");
    try { setRes((await api.get<Slots>("/signals/berth-slots", { params: { port: p } })).data); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  useEffect(() => { run(port); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Berth slot pressure, next 14 days</h2>
        <p className="mt-1 text-xs text-muted">Forecast dry-bulk traffic against the port's own busy level. Green days are when arriving ships are least likely to queue.</p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <Field label="Port"><select className={inputCls} value={port} onChange={(e) => { setPort(e.target.value); run(e.target.value); }}>{PORTS.map((p) => <option key={p}>{p}</option>)}</select></Field>
          {busy && <span className="pb-2 text-xs text-muted">Backtesting models…</span>}
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-4">
            <div className="h-56">
              <ResponsiveContainer>
                <BarChart data={res.days}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={36} domain={[0, 1.3]} />
                  <ReferenceLine y={1} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: "busy level", fontSize: 10, fill: "#64748b", position: "insideTopRight" }} />
                  <Tooltip formatter={(v) => [`${(Number(v) * 100).toFixed(0)}% of busy level`, "Pressure"]} />
                  <Bar dataKey="pressure" radius={[5, 5, 0, 0]} isAnimationActive={false}>{res.days.map((d) => <Cell key={d.date} fill={SLOT_COLOR[d.slot]} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Open days" value={res.open_days.length} tone={res.open_days.length ? "up" : "warn"} />
              <Stat label="Data through" value={res.data_through} />
              <Stat label="Chosen model" value={<span className="text-sm">{res.backtest.chosen_model}</span>} />
              <Stat label="Skill vs naive" value={res.backtest.skill_vs_naive_pct === null ? "n/a" : `${res.backtest.skill_vs_naive_pct}%`} tone={(res.backtest.skill_vs_naive_pct ?? 0) > 0 ? "up" : "warn"} />
            </div>
            <Note>{res.method} Backtest ({res.backtest.windows} windows) mean absolute error in calls/day: {Object.entries(res.backtest.mae_by_model).map(([k, v]) => `${k} ${v}`).join(", ")}. Gains over the naive forecast are small, so use this as a pressure indicator, not a schedule.</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

interface Transfer {
  significant_pairs: { from_port: string; to_port: string; lag_days: number; p_adjusted: number }[]; method: string; data_through: string;
  status: { port: string; recent_calls_per_day: number; baseline: number; z: number }[];
  signal: { hot_port: string; text: string; consider: string | null } | null;
}
function TransferTool() {
  const [res, setRes] = useState<Transfer | null>(null);
  useEffect(() => { api.get<Transfer>("/signals/transfer").then((r) => setRes(r.data)); }, []);
  if (!res) return <p className="text-sm text-muted">Computing cross-port relationships…</p>;
  return (
    <SpotlightCard>
      <div className="space-y-5 p-6">
        <div>
          <h2 className="text-sm font-semibold text-strong">Cross-port congestion transfer</h2>
          <p className="mt-1 text-xs text-muted">When traffic surges at one port, which others tend to follow, and how many days later? Ships diverted from a crowded port land elsewhere.</p>
        </div>
        {res.signal ? <Note kind="warn"><b>Rerouting signal.</b> {res.signal.text}</Note> : <Note>No port is unusually busy right now (all within 1 standard deviation of normal).</Note>}
        <div className="h-52">
          <ResponsiveContainer>
            <BarChart data={res.status}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
              <XAxis dataKey="port" tick={{ fontSize: 11, fill: "#334e68" }} />
              <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={36} />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Tooltip formatter={(v) => [`${Number(v).toFixed(2)} σ`, "vs normal"]} />
              <Bar isAnimationActive={false} dataKey="z" radius={[5, 5, 0, 0]}>{res.status.map((s) => <Cell key={s.port} fill={s.z > 1 ? "#dc2626" : s.z > 0.5 ? "#d97706" : "#059669"} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Statistically significant leads</h3>
          {res.significant_pairs.length === 0 ? <p className="mt-2 text-sm text-muted">None survive the multiple-testing correction.</p> : (
            <ul className="mt-2 space-y-2">
              {res.significant_pairs.map((p) => (
                <li key={p.from_port + p.to_port} className="flex items-center gap-2 text-sm text-body">
                  <b className="text-strong">{p.from_port}</b> <ArrowRight className="h-3.5 w-3.5 text-cyan" /> <b className="text-strong">{p.to_port}</b>
                  <span className="text-muted">after about {p.lag_days} days (adjusted p = {p.p_adjusted.toFixed(3)})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <Note>{res.method} Data through {res.data_through}.</Note>
      </div>
    </SpotlightCard>
  );
}

interface Cyclone {
  port: string; arrival_window_start: string; arrival_window_end: string; probability_storm_in_window: number; expected_storm_days: number; expected_delay_days: number;
  risk_label: string; safest_month: number; method: string; monthly: { month: number; storm_day_pct: number; severe_day_pct: number; storms_per_year: number }[];
  assumptions: { delay_days_per_storm_day: number; extra_delay_days_if_severe: number };
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function CycloneTool() {
  const today = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  const [port, setPort] = useState("Haldia");
  const [start, setStart] = useState(iso(new Date(today.getTime() + 30 * 864e5)));
  const [end, setEnd] = useState(iso(new Date(today.getTime() + 45 * 864e5)));
  const [transit, setTransit] = useState("20");
  const [res, setRes] = useState<Cyclone | null>(null);
  const [err, setErr] = useState("");
  async function run() {
    setErr("");
    try { setRes((await api.get<Cyclone>("/signals/cyclone", { params: { port, laycan_start: start, laycan_end: end, transit_days: Number(transit) } })).data); } catch (e) { setErr(errText(e)); }
  }
  const tone = res?.risk_label === "High" ? "down" : res?.risk_label === "Moderate" ? "warn" : "up";
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Cyclone-adjusted arrival risk</h2>
        <p className="mt-1 text-xs text-muted">Enter the loading window and sailing time; see the historical chance of a Bay of Bengal storm near the port when the ship arrives.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Field label="Discharge port"><select className={inputCls} value={port} onChange={(e) => setPort(e.target.value)}>{["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia", "Sagar / Sandheads"].map((p) => <option key={p}>{p}</option>)}</select></Field>
          <Field label="Laycan start"><input type="date" className={inputCls} value={start} onChange={(e) => setStart(e.target.value)} /></Field>
          <Field label="Laycan end"><input type="date" className={inputCls} value={end} onChange={(e) => setEnd(e.target.value)} /></Field>
          <Field label="Sailing days"><input className={inputCls} value={transit} onChange={(e) => setTransit(e.target.value)} /></Field>
          <div className="flex items-end"><button className={btnCls + " w-full"} onClick={run}>Assess</button></div>
        </div>
        {err && <p className="mt-3 text-xs text-down">{err}</p>}
        {res && (
          <div className="mt-5 space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Arrival window" value={<span className="text-sm">{res.arrival_window_start} to {res.arrival_window_end}</span>} />
              <Stat label="Storm chance in window" value={`${(res.probability_storm_in_window * 100).toFixed(0)}%`} tone={tone} />
              <Stat label="Expected delay" value={`${res.expected_delay_days} d`} tone={tone} />
              <Stat label="Risk" value={res.risk_label} tone={tone} />
            </div>
            <div className="h-48">
              <ResponsiveContainer>
                <BarChart data={res.monthly.map((m) => ({ ...m, name: MONTHS[m.month - 1] }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} width={36} unit="%" />
                  <Tooltip formatter={(v, n) => [`${v}%`, n === "storm_day_pct" ? "Days with a storm" : "Days with a severe storm"]} />
                  <Bar isAnimationActive={false} dataKey="storm_day_pct" fill="#0e7490" radius={[5, 5, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="severe_day_pct" fill="#dc2626" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Note>{res.method} Delay assumptions: {res.assumptions.delay_days_per_storm_day} days per storm day, plus {res.assumptions.extra_delay_days_if_severe} if severe (assumed, not measured). Long-run averages, not a weather forecast; the calmest month for this port is {MONTHS[res.safest_month - 1]}.</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

interface Demand {
  ratio_imported_to_crude: number; ratio_spread: number; method: string;
  points: { year: string; crude_steel_mt: number; imported_coal_mt: number; ratio: number }[];
  estimates: { period: string; crude_steel_mt: number; imported_coal_mt: number; low_mt: number; high_mt: number; parcels: number }[];
  next_quarter: { crude_steel_mt: number; imported_coal_mt: number; parcels: number; parcel_tonnes: number };
}
function DemandTool() {
  const [growth, setGrowth] = useState(0);
  const [parcel, setParcel] = useState(33000);
  const [res, setRes] = useState<Demand | null>(null);
  useEffect(() => { api.get<Demand>("/signals/demand", { params: { growth_pct: growth, parcel_tonnes: parcel } }).then((r) => setRes(r.data)); }, [growth, parcel]);
  return (
    <SpotlightCard>
      <div className="space-y-5 p-6">
        <div>
          <h2 className="text-sm font-semibold text-strong">How much coking coal will SAIL need to charter?</h2>
          <p className="mt-1 text-xs text-muted">Imported coal follows crude steel output. Move the slider to test a production plan and see the number of shiploads.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={`Next-quarter crude steel change vs Q1 FY27: ${growth > 0 ? "+" : ""}${growth}%`}><input type="range" min={-15} max={15} value={growth} onChange={(e) => setGrowth(Number(e.target.value))} className="mt-2 w-full accent-cyan" /></Field>
          <Field label="Parcel size (tonnes)"><select className={inputCls} value={parcel} onChange={(e) => setParcel(Number(e.target.value))}>{[33000, 55000, 75000, 150000].map((p) => <option key={p} value={p}>{p.toLocaleString()} t</option>)}</select></Field>
        </div>
        {res && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Crude steel, next quarter" value={`${res.next_quarter.crude_steel_mt} MT`} />
              <Stat label="Imported coking coal" value={`${res.next_quarter.imported_coal_mt} MT`} tone="warn" />
              <Stat label="Shiploads to charter" value={res.next_quarter.parcels} />
              <Stat label="Imported / crude steel" value={`${(res.ratio_imported_to_crude * 100).toFixed(1)}%`} />
            </div>
            <table className="w-full text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Period</th><th>Crude steel (reported)</th><th>Imported coal (estimated)</th><th>Range</th></tr></thead>
              <tbody>{res.estimates.map((e) => <tr key={e.period} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{e.period}</td><td>{e.crude_steel_mt} MT</td><td>{e.imported_coal_mt} MT</td><td className="text-muted">{e.low_mt}–{e.high_mt}</td></tr>)}</tbody>
            </table>
            <Note kind="warn">{res.method}</Note>
          </>
        )}
      </div>
    </SpotlightCard>
  );
}


export default function Signals() {
  const [tab, setTab] = useState<Tab>("slots");
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Port signals" subtitle="Forward-looking signals for the East Coast ports, built from real port-call data, cyclone history and SAIL's own output." />
      <Tabs<Tab> tabs={[{ key: "slots", label: "Berth slots" }, { key: "transfer", label: "Congestion transfer" }, { key: "cyclone", label: "Cyclone ETA risk" }, { key: "demand", label: "Coal demand" }]} value={tab} onChange={setTab} />
      {tab === "slots" && <SlotsTool />}
      {tab === "transfer" && <TransferTool />}
      {tab === "cyclone" && <CycloneTool />}
      {tab === "demand" && <DemandTool />}
    </div>
  );
}
