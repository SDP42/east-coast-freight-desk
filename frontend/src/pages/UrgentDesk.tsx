import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Gavel, Ship } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LightSelect from "../components/LightSelect";
import Loading from "../components/Loading";
import FuseButtonRaw from "../components/rb/FuseButton";
import { Note, PageHeader, Stat, errText } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const FuseButton = FuseButtonRaw as unknown as React.ComponentType<Record<string, unknown>>;
interface Option {
  origin: string; vessel_class: string; speed_knots: number; days: number; slack_days: number; p_on_time: number; total_inr_crore: number; total_usd: number; freight_usd_per_t: number;
  urgency_premium_pct: number; premium_usd: number; feasible: boolean; fits_berth: boolean; coking_grade: boolean; score: number;
}
interface Res { port: string; cargo_tonnes: number; deadline_days: number; storm_chance_in_window: number; verdict: string; best: Option | null; fastest: Option; walk_away_usd_per_t: number | null; options: Option[]; options_evaluated: number; feasible_count: number; method: string }
const PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"];

export default function UrgentDesk() {
  const { can } = useAuth();
  const [port, setPort] = useState("Paradip");
  const [cargo, setCargo] = useState(60000);
  const [days, setDays] = useState(20);
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [fixed, setFixed] = useState<string | null>(null);
  const tick = useRef(0);

  useEffect(() => {
    const mine = ++tick.current;
    setBusy(true);
    const t = setTimeout(async () => {
      try { const r = await api.post<Res>("/whatif/urgent", { port, cargo_tonnes: cargo, deadline_days: days }); if (mine === tick.current) { setRes(r.data); setErr(""); } }
      catch (e) { if (mine === tick.current) setErr(errText(e)); }
      finally { if (mine === tick.current) setBusy(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [port, cargo, days]);

  async function record(o: Option) {
    try {
      await api.post("/ledger", { fixture_date: new Date().toISOString().slice(0, 10), vessel_name: `Urgent desk ${o.vessel_class}`, origin_country: o.origin, destination_port: port, cargo_tonnes: cargo, charter_type: "spot", rate_usd_per_tonne: o.freight_usd_per_t, notes: `Fixed from the Urgent Desk: ${o.days} days at ${o.speed_knots} kn, ${Math.round(o.p_on_time * 100)}% on time` });
      setFixed(`${o.vessel_class} from ${o.origin} recorded in the fixture ledger`);
    } catch (e) { setErr(errText(e)); }
  }

  const max = Math.max(days * 1.35, ...(res?.options.map((o) => o.days) ?? [0]));
  const deadlinePct = (days / max) * 100;
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Urgent fixture desk" subtitle="A plant is short of coal and the clock is running. Set the port, the tonnes and the deadline: the desk tells you what can arrive in time, how likely it is, and the most you should pay." />

      <SpotlightCard>
        <div className="grid gap-5 p-5 sm:grid-cols-4">
          <LightSelect label="Discharge port" value={port} options={PORTS} onChange={setPort} width={200} />
          <label className="block text-xs font-medium text-body">Tonnes needed: {cargo.toLocaleString()}<input type="range" min={20000} max={200000} step={5000} value={cargo} onChange={(e) => setCargo(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
          <label className="block text-xs font-medium text-body">Deadline: {days} days<input type="range" min={7} max={45} step={1} value={days} onChange={(e) => setDays(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
          <div className="flex items-end text-xs text-muted">{busy ? <Loading label="Costing options" pattern="sweep" /> : res ? <span className="flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" />{res.options_evaluated} options evaluated</span> : null}</div>
        </div>
      </SpotlightCard>
      {err && <p className="mt-3 text-xs text-down">{err}</p>}

      {res && (
        <div className="mt-4 space-y-4">
          <div className={`flex items-start gap-3 rounded-2xl border p-5 ${res.best ? "border-up/30 bg-up/10" : "border-down/30 bg-down/10"}`}>
            {res.best ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-up" /> : <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-down" />}
            <div className="min-w-0 flex-1">
              <p className={`text-sm font-semibold ${res.best ? "text-up" : "text-down"}`}>{res.best ? "A safe option exists" : "Nothing safe reaches the port in time"}</p>
              <p className="mt-1 text-sm leading-relaxed text-body">{res.verdict}</p>
              {res.best && can("ledger:write") && (
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <FuseButton label="Fix this vessel" undoLabel="Undo" doneLabel="Recorded" commitOn="fuseEnd" undoWindow={5000} settle="stay" size="md" radius={14}
                    color="#ffffff" background="#0b2545" fuseColor="#f59e0b" icon={<Gavel size={15} />} onCommit={() => res.best && record(res.best)} />
                  <span className="text-xs text-muted">Recorded in the fixture ledger after 5 seconds unless you undo.</span>
                </div>
              )}
              {fixed && <p className="mt-2 text-xs font-medium text-up">{fixed}.</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Stat label="Deadline" value={`${res.deadline_days} days`} />
            <Stat label="Safe options" value={`${res.feasible_count} of ${res.options_evaluated}`} tone={res.feasible_count ? "up" : "down"} />
            <Stat label="Storm chance in window" value={`${Math.round(res.storm_chance_in_window * 100)}%`} tone={res.storm_chance_in_window > 0.3 ? "warn" : undefined} />
            <Stat label="Walk-away price" value={res.walk_away_usd_per_t ? `$${res.walk_away_usd_per_t}/t` : "n/a"} tone="warn" />
            <Stat label="Best cost" value={res.best ? `₹${res.best.total_inr_crore} cr` : "n/a"} />
          </div>

          <SpotlightCard>
            <div className="p-5">
              <p className="text-sm font-semibold text-strong">Options against the deadline</p>
              <p className="text-xs text-muted">Each bar is the trip length; the dashed line is your deadline. Red means it would land late.</p>
              <ul className="mt-4 space-y-3">
                {res.options.map((o, i) => {
                  const ok = o.feasible && o.fits_berth && o.coking_grade;
                  return (
                    <li key={i} className={`rounded-xl border p-3 ${res.best && o === res.options.find((x) => x.origin === res.best!.origin && x.vessel_class === res.best!.vessel_class && x.speed_knots === res.best!.speed_knots) ? "border-up/40 bg-up/5" : "border-border-soft"}`}>
                      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <span className="flex items-center gap-2 font-semibold text-strong"><Ship className="h-4 w-4 text-cyan" />{o.vessel_class} · {o.origin} · {o.speed_knots.toFixed(0)} kn
                          {!o.fits_berth && <span className="rounded bg-down/10 px-1.5 text-[10px] text-down">does not fit the berth</span>}
                          {!o.coking_grade && <span className="rounded bg-amber/10 px-1.5 text-[10px] text-amber">mostly thermal coal</span>}</span>
                        <span className="text-xs text-body">₹{o.total_inr_crore} cr · ${o.freight_usd_per_t}/t{o.urgency_premium_pct > 4 ? ` · +${o.urgency_premium_pct}% urgency` : ""}</span>
                      </div>
                      <div className="relative mt-2 h-3 rounded-full bg-panel-light">
                        <div className={`h-3 rounded-full ${ok ? "bg-cyan" : o.days > days ? "bg-down" : "bg-amber"}`} style={{ width: `${Math.min(100, (o.days / max) * 100)}%` }} />
                        <div className="absolute inset-y-[-4px] w-0.5 border-l-2 border-dashed border-strong/60" style={{ left: `${deadlinePct}%` }} />
                      </div>
                      <div className="mt-1 flex justify-between text-[11px] text-muted"><span>{o.days} days ({o.slack_days >= 0 ? `${o.slack_days} spare` : `${Math.abs(o.slack_days)} late`})</span><span className={o.p_on_time >= 0.8 ? "text-up" : "text-down"}>{Math.round(o.p_on_time * 100)}% on time</span></div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </SpotlightCard>
          <Note kind="warn">{res.method} Costs are illustrative estimates, not quotes.</Note>
        </div>
      )}
    </div>
  );
}
