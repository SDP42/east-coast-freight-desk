import { useEffect, useRef, useState } from "react";
import { CalendarClock, CheckCircle2, Hourglass, Scissors, ShieldAlert, Ship } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LightSelect from "../components/LightSelect";
import Loading from "../components/Loading";
import { Note, PageHeader, Stat, errText, Fine } from "../components/ui";
import { api } from "../lib/api";

interface Sig { signal: string; weight: number; vote: number; reading: string; why: string }
interface ShipOpt { origin: string; vessel_class: string; speed_knots: number; days: number; p_on_time: number; total_inr_crore: number; part_laden?: boolean }
interface Res {
  verdict: string; headline: string; score: number; confidence: string; act_by: string; port: string; cargo_tonnes: number; need_by_days: number;
  ship: ShipOpt | null; walk_away_usd_per_t: number | null; safe_options: number; options_evaluated: number; signals: Sig[]; what_would_change_it: string[]; notes: string[]; method: string;
}
const PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"];
const STYLE: Record<string, { box: string; text: string; Icon: typeof CheckCircle2 }> = {
  "RENT NOW": { box: "border-up/30 bg-up/10", text: "text-up", Icon: CheckCircle2 },
  "RENT WITHIN A WEEK": { box: "border-cyan/30 bg-cyan/10", text: "text-cyan", Icon: CalendarClock },
  "WAIT AND RECHECK": { box: "border-warn/30 bg-warn/10", text: "text-warn", Icon: Hourglass },
  "SPLIT INTO TWO PARCELS": { box: "border-cyan/30 bg-cyan/10", text: "text-cyan", Icon: Scissors },
  "CANNOT MEET THE DATE SAFELY": { box: "border-down/30 bg-down/10", text: "text-down", Icon: ShieldAlert },
};

export default function Verdict() {
  const [port, setPort] = useState("Paradip");
  const [cargo, setCargo] = useState(60000);
  const [days, setDays] = useState(30);
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const tick = useRef(0);

  useEffect(() => {
    const mine = ++tick.current;
    setBusy(true);
    const t = setTimeout(async () => {
      try { const r = await api.post<Res>("/verdict", { port, cargo_tonnes: cargo, need_by_days: days }); if (mine === tick.current) { setRes(r.data); setErr(""); } }
      catch (e) { if (mine === tick.current) setErr(errText(e)); }
      finally { if (mine === tick.current) setBusy(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [port, cargo, days]);

  const st = res ? STYLE[res.verdict] ?? STYLE["RENT WITHIN A WEEK"] : null;
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="The verdict" subtitle="When to rent a ship, and which one, in one plain answer." />
      <SpotlightCard>
        <div className="grid gap-5 p-5 sm:grid-cols-4">
          <LightSelect label="Discharge port" value={port} options={PORTS} onChange={setPort} width={200} />
          <label className="block text-xs font-medium text-body">Tonnes: {cargo.toLocaleString()}<input type="range" min={20000} max={200000} step={5000} value={cargo} onChange={(e) => setCargo(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
          <label className="block text-xs font-medium text-body">Needed within {days} days<input type="range" min={10} max={90} step={1} value={days} onChange={(e) => setDays(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
          <div className="flex items-end text-xs text-muted">{busy && <Loading label="Weighing the signals" pattern="sweep" />}</div>
        </div>
      </SpotlightCard>
      {err && <p className="mt-3 text-xs text-down">{err}</p>}

      {res && st && (
        <div className="mt-4 space-y-4">
          <div className={`rounded-2xl border p-6 ${st.box}`}>
            <div className="flex items-start gap-4">
              <st.Icon className={`mt-1 h-8 w-8 shrink-0 ${st.text}`} />
              <div className="min-w-0">
                <p className={`text-xs font-semibold uppercase tracking-widest ${st.text}`}>{res.verdict}</p>
                <p className="mt-2 text-lg font-semibold leading-snug text-strong sm:text-xl">{res.headline}</p>
                <p className="mt-2 text-sm text-body">Act by <span className="font-medium text-strong">{new Date(res.act_by).toLocaleDateString(undefined, { day: "numeric", month: "long" })}</span> · Confidence <span className="font-medium text-strong">{res.confidence}</span>{res.walk_away_usd_per_t ? <> · Do not pay more than about <span className="font-medium text-strong">${res.walk_away_usd_per_t}/t</span></> : null}</p>
              </div>
            </div>
          </div>

          {res.ship && (
            <div className="grid gap-3 sm:grid-cols-4">
              <Stat label="Ship" value={<span className="flex items-center gap-1.5"><Ship className="h-4 w-4" />{res.ship.vessel_class}</span>} />
              <Stat label="From" value={res.ship.origin} />
              <Stat label="Arrives in" value={`${res.ship.days.toFixed(0)} days`} />
              <Stat label="On time" value={`${Math.round(res.ship.p_on_time * 100)}%`} tone={res.ship.p_on_time >= 0.8 ? "up" : "down"} />
            </div>
          )}

          <SpotlightCard>
            <div className="p-5">
              <h3 className="text-sm font-semibold text-strong">Why: what the desk weighed</h3>
              <div className="mt-3 space-y-3">
                {res.signals.map((s) => (
                  <div key={s.signal} className="grid items-center gap-3 sm:grid-cols-[11rem_1fr]">
                    <div><p className="text-sm font-medium text-strong">{s.signal}</p><p className="text-xs text-muted">{s.reading}</p></div>
                    <div>
                      <div className="relative h-2.5 rounded-full bg-border-soft" aria-label={`vote ${s.vote}`}>
                        <span className="absolute left-1/2 top-0 h-full w-px bg-muted/50" />
                        <span className={`absolute top-0 h-full rounded-full ${s.vote >= 0 ? "bg-up" : "bg-warn"}`} style={{ left: s.vote >= 0 ? "50%" : `${50 + s.vote * 50}%`, width: `${Math.abs(s.vote) * 50}%` }} />
                      </div>
                      <p className="mt-1 text-xs text-body">{s.why}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted">Bars to the right favour renting now; bars to the left favour waiting. Overall score {res.score > 0 ? "+" : ""}{res.score}.</p>
            </div>
          </SpotlightCard>

          {res.what_would_change_it.length > 0 && <SpotlightCard><div className="p-5"><h3 className="text-sm font-semibold text-strong">What would change this call</h3><ul className="mt-2 space-y-1 text-sm text-body">{res.what_would_change_it.map((w) => <li key={w}>• {w}</li>)}</ul></div></SpotlightCard>}
          {res.notes.map((n) => <Note key={n} kind="warn">{n}</Note>)}
          <Fine>{res.method}</Fine>
        </div>
      )}
    </div>
  );
}
