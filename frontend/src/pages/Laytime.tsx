import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader, Stat, btnCls, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";

interface Res { result: string; amount_usd: number; days: number; laytime_allowed_days: number; time_used_hours: number; on_demurrage: boolean; steps: string[] }
interface Stop { label: string; hours: number; after_laytime: boolean }

export default function Laytime() {
  const [f, setF] = useState({ cargo_tonnes: 75000, rate_tonnes_per_day: 20000, hours_nor_to_complete: 120, notice_hours: 6, demurrage_usd_per_day: 20000 });
  const [stops, setStops] = useState<Stop[]>([{ label: "Rain", hours: 10, after_laytime: false }]);
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: Number(e.target.value) });
  const run = () => api.post<Res>("/laytime", { ...f, stoppages: stops }).then((r) => { setRes(r.data); setErr(""); }).catch((e) => setErr(errText(e)));
  const fields: [keyof typeof f, string][] = [["cargo_tonnes", "Cargo (t)"], ["rate_tonnes_per_day", "Agreed rate (t/day)"], ["hours_nor_to_complete", "Hours, notice of readiness to completion"], ["notice_hours", "Notice period (h)"], ["demurrage_usd_per_day", "Demurrage rate ($/day)"]];

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Laytime and demurrage claims" subtitle="Check a demurrage or despatch claim, step by step." />
      <SpotlightCard>
        <div className="grid gap-4 p-5 sm:grid-cols-3">
          {fields.map(([k, l]) => (<label key={k} className="block text-xs font-medium text-body">{l}<input type="number" className={inputCls} value={f[k]} onChange={set(k)} /></label>))}
        </div>
        <div className="border-t border-border-soft p-5">
          <p className="text-xs font-medium text-body">Excepted periods (rain, strikes, shore breakdowns)</p>
          <div className="mt-2 space-y-2">
            {stops.map((s, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2">
                <input className={`${inputCls} !mt-0 w-40`} value={s.label} onChange={(e) => setStops(stops.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} />
                <input type="number" className={`${inputCls} !mt-0 w-28`} value={s.hours} onChange={(e) => setStops(stops.map((x, j) => (j === i ? { ...x, hours: Number(e.target.value) } : x)))} />
                <span className="text-xs text-muted">hours</span>
                <label className="flex items-center gap-1.5 text-xs text-body"><input type="checkbox" checked={s.after_laytime} onChange={(e) => setStops(stops.map((x, j) => (j === i ? { ...x, after_laytime: e.target.checked } : x)))} />after laytime expired</label>
                <button onClick={() => setStops(stops.filter((_, j) => j !== i))} aria-label="Remove" className="text-muted hover:text-down"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
            <button onClick={() => setStops([...stops, { label: "Rain", hours: 0, after_laytime: false }])} className="flex items-center gap-1 text-xs text-muted hover:text-strong"><Plus className="h-3.5 w-3.5" />Add period</button>
          </div>
          <button onClick={run} className={`${btnCls} mt-4`}>Calculate claim</button>
        </div>
      </SpotlightCard>
      {err && <p className="mt-3 text-xs text-down">{err}</p>}
      {res && (
        <div className="mt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Outcome" value={res.result} tone={res.on_demurrage ? "down" : "up"} />
            <Stat label="Amount" value={`$${res.amount_usd.toLocaleString()}`} />
            <Stat label="Laytime allowed" value={`${res.laytime_allowed_days} d`} />
            <Stat label="Time counted" value={`${res.time_used_hours} h`} />
          </div>
          <SpotlightCard><ol className="space-y-2 p-5 text-sm text-body">{res.steps.map((s, i) => (<li key={i}><span className="mr-2 font-medium text-strong">{i + 1}.</span>{s}</li>))}</ol></SpotlightCard>
          <Note>Working tool for checking a claim, not legal advice. The charter party governs; despatch is taken at half the demurrage rate, which is customary but negotiable.</Note>
        </div>
      )}
    </div>
  );
}
