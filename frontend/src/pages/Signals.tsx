import { useEffect, useState } from "react";
import { px } from "../lib/scale";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import SpotlightCard from "../components/SpotlightCard";
import { Field, PageHeader, Stat, Tabs, btnCls, errText, inputCls, Fine } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

type Tab = "cyclone" | "demand" | "lightering" | "timing";
const ALL_CYCLONE_PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia", "Sagar / Sandheads"];

interface Cyclone {
  port: string; arrival_window_start: string; arrival_window_end: string; probability_storm_in_window: number; expected_storm_days: number; expected_delay_days: number;
  risk_label: string; safest_month: number; method: string; monthly: { month: number; storm_day_pct: number; severe_day_pct: number; storms_per_year: number }[];
  assumptions: { delay_days_per_storm_day: number; extra_delay_days_if_severe: number };
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function CycloneTool() {
  const { user } = useAuth();
  const cyclonePorts = ALL_CYCLONE_PORTS.filter((p) => !user?.port_scope || user.port_scope.includes(p));
  const today = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  const [port, setPort] = useState(cyclonePorts.includes("Haldia") ? "Haldia" : cyclonePorts[0] ?? "Haldia");
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
          <Field label="Discharge port"><select className={inputCls} value={port} onChange={(e) => setPort(e.target.value)}>{cyclonePorts.map((p) => <option key={p}>{p}</option>)}</select></Field>
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
                  <XAxis dataKey="name" tick={{ fontSize: px(11), fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: px(11), fill: "#64748b" }} width={px(36)} unit="%" />
                  <Tooltip formatter={(v, n) => [`${v}%`, n === "storm_day_pct" ? "Days with a storm" : "Days with a severe storm"]} />
                  <Bar isAnimationActive={false} dataKey="storm_day_pct" fill="#0e7490" radius={[5, 5, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="severe_day_pct" fill="#dc2626" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Fine>{res.method} Delay assumptions: {res.assumptions.delay_days_per_storm_day} days per storm day, plus {res.assumptions.extra_delay_days_if_severe} if severe (assumed, not measured). Long-run averages, not a weather forecast; the calmest month for this port is {MONTHS[res.safest_month - 1]}.</Fine>
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
            <Fine>{res.method}</Fine>
          </>
        )}
      </div>
    </SpotlightCard>
  );
}


interface Lightering {
  regression: null; points: { draft: number; tonnes: number }[];
  draft_ceiling_m: number; max_cargo_at_ceiling_t: number; regression_cargo_at_ceiling_t: number; fit_quality: string; cargo_tonnes: number; tonnes_to_lighten: number;
  barge_trips: number; lightering_days: number; parcels_of_median_size: number; median_parcel_t: number; assumptions: { barge_capacity_t: number; barge_cycle_days: number }; method: string;
}
function LighteringTool() {
  const [cargo, setCargo] = useState(150000);
  const [d, setD] = useState<Lightering | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.get<Lightering>("/lab/lightering", { params: { cargo_tonnes: cargo } }).then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, [cargo]);
  return (
    <SpotlightCard>
      <div className="space-y-5 p-6">
        <div>
          <h2 className="text-sm font-semibold text-strong">Haldia lightering planner</h2>
          <p className="mt-1 text-xs text-muted">Big ships cannot sail the Hooghly fully laden. Drag the cargo to see how much is lightened at Sagar. The 35,000 t ceiling is an assumption; replace it with SAIL's figure.</p>
        </div>
        <Field label={`Cargo on the mother vessel: ${cargo.toLocaleString()} t`}><input type="range" min={40000} max={250000} step={5000} value={cargo} onChange={(e) => setCargo(Number(e.target.value))} className="mt-2 w-full accent-cyan" /></Field>
        {err && <p className="text-xs text-down">{err}</p>}
        {d && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <Stat label="Assumed Haldia ceiling" value={`${d.max_cargo_at_ceiling_t.toLocaleString()} t`} />
              <Stat label="To lighten at Sagar" value={`${d.tonnes_to_lighten.toLocaleString()} t`} tone={d.tonnes_to_lighten > 0 ? "warn" : "up"} />
              <Stat label="Barge trips" value={d.barge_trips} /><Stat label="Lightering days" value={d.lightering_days} />
              <Stat label="Parcels at the ceiling" value={`${d.parcels_of_median_size} × ${d.median_parcel_t.toLocaleString()} t`} />
            </div>
            <Fine>{d.method}</Fine>
          </>
        )}
      </div>
    </SpotlightCard>
  );
}

interface Timing { port: string; origin: string; transit_days: number; cells: { laycan_start: string; storm_probability: number; score: number }[]; best: { laycan_start: string; storm_probability: number; score: number }[]; method: string; note: string }
function TimingCoach() {
  const { user } = useAuth();
  const ports = ALL_CYCLONE_PORTS.filter((p) => !user?.port_scope || user.port_scope.includes(p));
  const [port, setPort] = useState(ports.includes("Haldia") ? "Haldia" : ports[0] ?? "Haldia");
  const [origin, setOrigin] = useState("Australia");
  const [d, setD] = useState<Timing | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setErr(""); api.get<Timing>("/lab/timing", { params: { port, origin } }).then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, [port, origin]);
  const color = (s: number) => (s > 0.85 ? "bg-up" : s > 0.7 ? "bg-up/60" : s > 0.55 ? "bg-amber/70" : "bg-down/80");
  return (
    <SpotlightCard>
      <div className="space-y-5 p-6">
        <div>
          <h2 className="text-sm font-semibold text-strong">Laycan timing coach</h2>
          <p className="mt-1 text-xs text-muted">For each possible loading date over the next 60 days: how likely is a Bay of Bengal storm during the week the ship arrives?</p>
        </div>
        <div className="flex flex-wrap gap-4">
          <Field label="Discharge port"><select className={inputCls} value={port} onChange={(e) => setPort(e.target.value)}>{ports.map((p) => <option key={p}>{p}</option>)}</select></Field>
          <Field label="Origin"><select className={inputCls} value={origin} onChange={(e) => setOrigin(e.target.value)}>{["Australia", "United States", "Mozambique", "Russia", "Indonesia"].map((o) => <option key={o}>{o}</option>)}</select></Field>
        </div>
        {err && <p className="text-xs text-down">{err}</p>}
        {d && (
          <>
            <div className="grid grid-cols-10 gap-1 sm:grid-cols-12">
              {d.cells.map((c) => <div key={c.laycan_start} title={`${c.laycan_start}: ${Math.round(c.storm_probability * 100)}% chance of a storm in the arrival week`} className={`aspect-square rounded-md ${color(c.score)} transition hover:scale-110`} />)}
            </div>
            <div className="flex items-center gap-2 text-[11px] text-muted"><span>riskier</span><span className="h-2 w-28 rounded-full" style={{ background: "linear-gradient(90deg,#dc2626,#d97706,#059669)" }} /><span>calmer</span><span className="ml-auto">{d.cells[0].laycan_start} to {d.cells[d.cells.length - 1].laycan_start}</span></div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Five calmest laycan starts (sailing {d.transit_days} days)</p>
              <ul className="mt-2 flex flex-wrap gap-2">{d.best.map((b) => <li key={b.laycan_start} className="rounded-full border border-up/30 bg-up/10 px-3 py-1 text-xs text-up">{b.laycan_start} · {Math.round(b.storm_probability * 100)}% storm chance</li>)}</ul>
            </div>
            <Fine>{d.method} {d.note}</Fine>
          </>
        )}
      </div>
    </SpotlightCard>
  );
}

export default function Signals() {
  const { can, user } = useAuth();
  const [tab, setTab] = useState<Tab>("cyclone");
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Port signals" subtitle="Cyclone risk, laycan timing and demand signals for the East Coast ports." />
      <Tabs<Tab> tabs={[{ key: "cyclone", label: "Cyclone ETA risk" }, { key: "timing", label: "Timing coach" }, ...(!user?.port_scope || user.port_scope.includes("Haldia") ? [{ key: "lightering" as Tab, label: "Haldia lightering" }] : []), ...(can("demand:read") ? [{ key: "demand" as Tab, label: "Coal demand" }] : [])]} value={tab} onChange={setTab} />
      {tab === "cyclone" && <CycloneTool />}
      {tab === "demand" && <DemandTool />}
      {tab === "lightering" && <LighteringTool />}
      {tab === "timing" && <TimingCoach />}
    </div>
  );
}
