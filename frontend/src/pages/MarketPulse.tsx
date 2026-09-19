import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Loading from "../components/Loading";
import { Note, PageHeader, errText } from "../components/ui";
import { api } from "../lib/api";

interface Card { series: string; label: string; unit: string; latest: number; as_of: string; change_3m_pct: number | null; change_12m_pct: number | null; percentile_since_start: number; history_from: string }
interface Res { cards: Card[]; headlines: string[]; note: string }

const Pct = ({ v }: { v: number | null }) => v == null ? <span className="text-muted">n/a</span> : (
  <span className={`inline-flex items-center gap-0.5 font-medium ${v >= 0 ? "text-up" : "text-down"}`}>{v >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}{Math.abs(v).toFixed(1)}%</span>
);

export default function MarketPulse() {
  const [d, setD] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.get<Res>("/market/pulse").then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, []);
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Market pulse" subtitle="What the current public-domain data says today: freight, fuel, coal and currency, all US-government or Federal Reserve series, current to 2026." />
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
          <Note>{d.note} Sources: USDA Agricultural Marketing Service, US Bureau of Labor Statistics, US Energy Information Administration and the Federal Reserve (via FRED).</Note>
        </div>
      )}
    </div>
  );
}
