import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Loading from "../components/Loading";
import { Note, PageHeader, errText } from "../components/ui";
import { api } from "../lib/api";

interface Card { series: string; label: string; unit: string; latest: number; as_of: string; change_3m_pct: number | null; change_12m_pct: number | null; percentile_since_start: number; history_from: string }
interface PortRow { port: string; calls_per_day_28d: number; vs_previous_28d_pct: number | null; vs_year_ago_pct: number | null; dry_bulk_import_kt_28d: number; import_vs_year_ago_pct: number | null }
interface Choke { chokepoint: string; dry_bulk_dwt_per_day_28d: number; vs_year_ago_pct: number | null; vs_pre_oct_2023_pct: number | null }
interface Res { cards: Card[]; ports: PortRow[]; chokepoints: Choke[]; headlines: string[]; ports_as_of: string; chokepoints_as_of: string; note: string }

const Pct = ({ v }: { v: number | null }) => v == null ? <span className="text-muted">n/a</span> : (
  <span className={`inline-flex items-center gap-0.5 font-medium ${v >= 0 ? "text-up" : "text-down"}`}>{v >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}{Math.abs(v).toFixed(1)}%</span>
);

export default function MarketPulse() {
  const [d, setD] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.get<Res>("/market/pulse").then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, []);
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Market pulse" subtitle="What the current public data says today: prices to mid-2026 and dry-bulk traffic to last week. The Baltic indices themselves end in 2019, so these are the live, free, dry-bulk-relevant signals." />
      {err && <p className="text-xs text-down">{err}</p>}
      {!d && !err && <Loading label="Reading current data" pattern="sweep" block />}
      {d && (
        <div className="space-y-4">
          <SpotlightCard><ul className="space-y-1.5 p-5 text-sm text-body">{d.headlines.map((h) => <li key={h}>• {h}</li>)}</ul></SpotlightCard>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {d.cards.map((c) => (
              <SpotlightCard key={c.series}>
                <div className="p-4">
                  <p className="text-xs text-muted">{c.label}</p>
                  <p className="mt-1 text-2xl font-semibold text-strong">{c.latest.toLocaleString(undefined, { maximumFractionDigits: 2 })} <span className="text-xs font-normal text-muted">{c.unit}</span></p>
                  <div className="mt-2 flex gap-4 text-xs text-body"><span>3 mo <Pct v={c.change_3m_pct} /></span><span>12 mo <Pct v={c.change_12m_pct} /></span></div>
                  <p className="mt-2 text-xs text-muted">As of {c.as_of} · {c.percentile_since_start}th percentile since {c.history_from.slice(0, 4)}</p>
                </div>
              </SpotlightCard>
            ))}
          </div>
          <SpotlightCard>
            <div className="overflow-x-auto p-5">
              <h3 className="text-sm font-semibold text-strong">East Coast ports: dry-bulk calls, last 28 days (to {d.ports_as_of})</h3>
              <table className="mt-3 w-full text-left text-xs"><thead className="text-muted"><tr><th className="py-1">Port</th><th>Calls per day</th><th>vs previous 28 d</th><th>vs year ago</th><th>Import kt (AIS est.)</th><th>Import vs year ago</th></tr></thead>
                <tbody>{d.ports.map((p) => (<tr key={p.port} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{p.port}</td><td>{p.calls_per_day_28d}</td><td><Pct v={p.vs_previous_28d_pct} /></td><td><Pct v={p.vs_year_ago_pct} /></td><td>{p.dry_bulk_import_kt_28d.toLocaleString()}</td><td><Pct v={p.import_vs_year_ago_pct} /></td></tr>))}</tbody></table>
            </div>
          </SpotlightCard>
          <SpotlightCard>
            <div className="overflow-x-auto p-5">
              <h3 className="text-sm font-semibold text-strong">Chokepoints: dry-bulk capacity per day, last 28 days (to {d.chokepoints_as_of})</h3>
              <table className="mt-3 w-full text-left text-xs"><thead className="text-muted"><tr><th className="py-1">Chokepoint</th><th>Dwt per day</th><th>vs year ago</th><th>vs pre-Oct 2023</th></tr></thead>
                <tbody>{d.chokepoints.map((k) => (<tr key={k.chokepoint} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{k.chokepoint}</td><td>{k.dry_bulk_dwt_per_day_28d.toLocaleString()}</td><td><Pct v={k.vs_year_ago_pct} /></td><td><Pct v={k.vs_pre_oct_2023_pct} /></td></tr>))}</tbody></table>
            </div>
          </SpotlightCard>
          <Note>{d.note} Sources: IMF PortWatch (AIS-derived estimates), IMF commodity prices and US BLS via FRED, FRED exchange rates.</Note>
        </div>
      )}
    </div>
  );
}
