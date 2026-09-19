import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Gauge, ExternalLink } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import {
  getDisruptionEvents, getRouteRisk, getPorts,
  type DisruptionEvent, type RouteRisk, type Port,
} from "../lib/api";

const ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"];

const LABEL_COLOR: Record<string, string> = {
  Low: "text-up border-up/30 bg-up/10",
  Moderate: "text-amber border-amber/30 bg-amber/10",
  High: "text-down border-down/30 bg-down/10",
  Severe: "text-down border-down/50 bg-down/20",
};

export default function Risk() {
  const [events, setEvents] = useState<DisruptionEvent[]>([]);
  const [ports, setPorts] = useState<Port[]>([]);
  const [origin, setOrigin] = useState(ORIGINS[0]);
  const [destinationPort, setDestinationPort] = useState<number | null>(null);
  const [risk, setRisk] = useState<RouteRisk | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDisruptionEvents(), getPorts()])
      .then(([e, p]) => {
        setEvents(e);
        setPorts(p);
        setDestinationPort(p[0]?.id ?? null);
      })
      .catch(() => setError("Could not load risk data from the backend."));
  }, []);

  async function runScore() {
    if (destinationPort == null) return;
    setLoading(true);
    try {
      const r = await getRouteRisk(origin, destinationPort);
      setRisk(r);
    } catch {
      setError("Risk score request failed — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-strong">
        Risk &amp; Disruptions
      </motion.h1>

      {error && (
        <SpotlightCard glowColor="248,113,113">
          <p className="p-4 text-sm text-down">{error}</p>
        </SpotlightCard>
      )}

      <SpotlightCard>
        <div className="p-6">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
            <Gauge className="h-4 w-4 text-cyan" /> Composite Route Risk Score
          </h2>
          <p className="mt-1 text-xs text-muted">
            Combines disruption exposure, port congestion, and 90-day freight volatility into one score.
          </p>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <label className="text-sm text-muted">
              Origin country
              <select
                className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-strong"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
              >
                {ORIGINS.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </label>
            <label className="text-sm text-muted">
              Destination port
              <select
                className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-strong"
                value={destinationPort ?? ""}
                onChange={(e) => setDestinationPort(Number(e.target.value))}
              >
                {ports.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
            <div className="flex items-end">
              <button
                onClick={runScore}
                disabled={loading || destinationPort == null}
                className="w-full rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50"
              >
                {loading ? "Scoring…" : "Compute risk score"}
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {risk && (
              <motion.div key={`${risk.origin_country}-${risk.destination_port_name}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
                <div className={`flex items-center justify-between rounded-lg border p-4 ${LABEL_COLOR[risk.risk_label] ?? ""}`}>
                  <span className="text-sm font-medium">
                    {risk.origin_country} → {risk.destination_port_name}
                  </span>
                  <span className="text-2xl font-bold">
                    {risk.composite_score}/10 <span className="text-sm font-medium">({risk.risk_label})</span>
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {risk.factors.map((f) => (
                    <div key={f.name} className="rounded-md border border-border-soft bg-panel-light/50 p-3 text-xs">
                      <div className="flex items-center justify-between font-medium text-strong">
                        <span>{f.name.replace(/_/g, " ")}</span>
                        <span>{f.score}/10</span>
                      </div>
                      <p className="mt-1 text-muted">{f.detail}</p>
                    </div>
                  ))}
                </div>

                {risk.relevant_events.length > 0 && (
                  <div className="mt-3 text-xs text-muted">
                    Contributing events: {risk.relevant_events.map((e) => e.title).join(", ")}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </SpotlightCard>

      <h2 className="text-sm font-semibold text-strong">Documented Disruption Events</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {events.map((e, i) => (
          <motion.div key={e.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
            <SpotlightCard glowColor="248,113,113">
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-wide text-muted">
                    {e.category.replace(/_/g, " ")} · {e.start_date}
                    {e.end_date && ` – ${e.end_date}`}
                  </p>
                  <span className="flex items-center gap-1 text-[10px] text-amber">
                    <ShieldAlert className="h-3 w-3" /> impact {e.impact_score}/10
                  </span>
                </div>
                <p className="mt-1 text-sm font-medium text-strong">{e.title}</p>
                <p className="mt-1 text-xs text-muted">{e.region}</p>
                {e.source_url && (
                  <a href={e.source_url} target="_blank" rel="noreferrer" className="mt-2 flex items-center gap-1 text-[10px] text-cyan hover:underline">
                    <ExternalLink className="h-3 w-3" /> Source
                  </a>
                )}
              </div>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
