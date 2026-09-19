import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Globe2, Info } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LiveChart from "../components/LiveChart";
import Sparkline from "../components/Sparkline";
import { api, getRegions, type RegionBoard, type RegionSeries } from "../lib/api";

interface Anomaly { series: string; window: string; move_pct: number; z: number; as_of: string }

function AnomalyFeed() {
  const [items, setItems] = useState<Anomaly[] | null>(null);
  useEffect(() => { api.get<{ items: Anomaly[] }>("/lab/anomalies").then((r) => setItems(r.data.items)).catch(() => setItems([])); }, []);
  if (items === null) return null;
  return (
    <SpotlightCard>
      <div className="p-5">
        <p className="text-sm font-semibold text-strong">Unusual moves</p>
        <p className="mt-0.5 text-xs text-muted">Series whose latest move is at least two standard deviations from their own recent behaviour.</p>
        {items.length === 0 ? <p className="mt-3 text-sm text-muted">Nothing unusual right now.</p> : (
          <div className="mt-3 flex flex-wrap gap-2">
            {items.map((a) => (
              <span key={a.series + a.window} className={`rounded-full border px-3 py-1 text-xs ${a.move_pct < 0 ? "border-down/30 bg-down/10 text-down" : "border-up/30 bg-up/10 text-up"}`} title={`z = ${a.z}`}>
                {a.series} {a.move_pct > 0 ? "+" : ""}{a.move_pct}% over {a.window} <span className="opacity-70">(as of {a.as_of})</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}

export default function Markets() {
  const [boards, setBoards] = useState<RegionBoard[]>([]);
  const [selected, setSelected] = useState<RegionSeries | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getRegions()
      .then((b) => {
        setBoards(b);
        setSelected(b.flatMap((x) => x.series).find((s) => s.index_name === "OCEAN_GULF_JAPAN") ?? null);
      })
      .catch(() => setError(true));
  }, []);

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-strong">Markets</h1>
        <p className="mt-1 flex items-start gap-1.5 text-xs text-muted">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Charts replay real historical data at accelerated speed so spikes and collapses play out on screen. Every series is public-domain
          US-government or Federal Reserve data, current to 2026: the USDA grain ocean rate (a dry-bulk proxy), US freight and coal price indices, Brent crude and exchange rates.
        </p>
      </motion.div>

      <AnomalyFeed />

      {error && <p className="text-sm text-down">Could not load market data — is the backend running?</p>}

      {selected && (
        <SpotlightCard>
          <div className="p-6">
            <LiveChart indexName={selected.index_name} label={`${selected.label} (${selected.index_name})`} height={320} />
          </div>
        </SpotlightCard>
      )}

      <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
        <Globe2 className="h-4 w-4 text-cyan" /> Regional boards
        <span className="text-xs font-normal text-muted">click a row to chart it</span>
      </h2>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {boards.map((b, i) => (
          <motion.div key={b.region} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <SpotlightCard className={b.series.length === 0 ? "border-dashed" : ""}>
              <div className="p-4">
                <h3 className="text-sm font-semibold text-strong">{b.region}</h3>
                <p className="mt-0.5 text-[11px] text-muted">{b.note}</p>
                <div className="mt-3 divide-y divide-border-soft/60">
                  {b.series.map((s) => {
                    const up = (s.change_pct ?? 0) >= 0;
                    const active = selected?.index_name === s.index_name;
                    return (
                      <button
                        key={s.index_name}
                        onClick={() => setSelected(s)}
                        className={`flex w-full items-center gap-3 rounded px-2 py-2 text-left transition hover:bg-panel-light/60 ${active ? "bg-panel-light" : ""}`}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs text-body">{s.label}</p>
                          <p className="text-[10px] text-muted">as of {s.date}</p>
                        </div>
                        <Sparkline values={s.spark} up={up} />
                        <div className="w-24 text-right">
                          <p className="text-sm font-semibold tabular-nums text-strong">{s.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                          <p className={`text-[11px] tabular-nums ${up ? "text-up" : "text-down"}`}>
                            {s.change_pct != null ? `${up ? "▲" : "▼"} ${Math.abs(s.change_pct).toFixed(2)}%` : "—"}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                  {b.series.length === 0 && <p className="py-3 text-xs text-muted">Nothing to chart — no real series to show rather than an invented one.</p>}
                </div>
              </div>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
