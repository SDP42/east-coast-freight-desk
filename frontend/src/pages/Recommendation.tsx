import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trophy, CheckCircle2, XCircle, TrendingDown, TrendingUp, Ship } from "lucide-react";
import ParetoCard from "../components/ParetoCard";
import SpotlightCard from "../components/SpotlightCard";
import { getPorts, compareOrigins, type Port, type RecommendationResponse } from "../lib/api";

export default function Recommendation() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [destinationPort, setDestinationPort] = useState<number | null>(null);
  const [cargoTonnes, setCargoTonnes] = useState("75000");
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPorts()
      .then((p) => {
        setPorts(p);
        setDestinationPort(p[0]?.id ?? null);
      })
      .catch(() => setError("Could not load ports from the backend."));
  }, []);

  async function runCompare() {
    if (destinationPort == null) return;
    setLoading(true);
    setError(null);
    try {
      const res = await compareOrigins(destinationPort, Number(cargoTonnes));
      setResult(res);
    } catch {
      setError("Comparison failed — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-strong">
        Chartering Recommendation
      </motion.h1>

      <SpotlightCard>
        <div className="p-6">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
            <Ship className="h-4 w-4 text-cyan" /> Multi-Origin Comparative Routing
          </h2>
          <p className="mt-1 text-xs text-muted">
            Ranks Australia, US, Mozambique, Russia and Indonesia simultaneously for one cargo requirement —
            combining live port compatibility, route distance, and the current freight-market forecast.
          </p>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
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
            <label className="text-sm text-muted">
              Cargo tonnage
              <input
                type="number"
                className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-strong"
                value={cargoTonnes}
                onChange={(e) => setCargoTonnes(e.target.value)}
              />
            </label>
            <div className="flex items-end">
              <button
                onClick={runCompare}
                disabled={loading || destinationPort == null}
                className="w-full rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50"
              >
                {loading ? "Comparing origins…" : "Compare all 5 origins"}
              </button>
            </div>
          </div>

          {error && <p className="mt-4 text-sm text-down">{error}</p>}
        </div>
      </SpotlightCard>

      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <p className="text-xs text-muted">{result.methodology_note}</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {result.recommendations.map((rec, i) => {
                const isBest = rec.rank === 1 && rec.compatibility.compatible;
                const down = (rec.market_index_forecast_change_pct ?? 0) < 0;
                return (
                  <motion.div
                    key={rec.origin_country}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.07 }}
                  >
                    <SpotlightCard glowColor={isBest ? "52,211,153" : "34,211,238"} className={isBest ? "ring-1 ring-up/40" : ""}>
                      <div className="p-5">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-semibold text-strong">{rec.origin_country}</h3>
                          {isBest && (
                            <span className="flex items-center gap-1 rounded-full bg-up/10 px-2 py-0.5 text-[10px] font-medium text-up">
                              <Trophy className="h-3 w-3" /> Best option
                            </span>
                          )}
                        </div>

                        <div className="mt-3 flex items-center gap-1.5 text-xs">
                          {rec.compatibility.compatible ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-up" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-down" />
                          )}
                          <span className={rec.compatibility.compatible ? "text-up" : "text-down"}>
                            {rec.vessel_class_name} {rec.compatibility.compatible ? "fits" : "does not fit"} {result.destination_port_name}
                          </span>
                        </div>

                        <p className="mt-3 text-2xl font-bold text-strong">
                          {rec.estimated_total_cost_usd != null
                            ? `$${(rec.estimated_total_cost_usd / 1000).toLocaleString(undefined, { maximumFractionDigits: 0 })}k`
                            : "—"}
                        </p>
                        <p className="text-xs text-muted">
                          {rec.estimated_freight_usd_per_tonne != null ? `$${rec.estimated_freight_usd_per_tonne}/tonne` : "cost unknown"}
                          {rec.distance_nm != null && ` · ${rec.distance_nm.toLocaleString()} nm`}
                          {rec.typical_transit_days != null && ` · ~${rec.typical_transit_days}d transit`}
                        </p>

                        {rec.market_index_used && (
                          <div className={`mt-3 flex items-center gap-1.5 text-xs ${down ? "text-up" : "text-down"}`}>
                            {down ? <TrendingDown className="h-3.5 w-3.5" /> : <TrendingUp className="h-3.5 w-3.5" />}
                            {rec.market_index_used} forecast {down ? "softening" : "firming"}{" "}
                            {rec.market_index_forecast_change_pct != null && `${Math.abs(rec.market_index_forecast_change_pct).toFixed(2)}%`}
                          </div>
                        )}
                      </div>
                    </SpotlightCard>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <ParetoCard portId={destinationPort} cargoTonnes={Number(cargoTonnes) || 0} />
    </div>
  );
}
