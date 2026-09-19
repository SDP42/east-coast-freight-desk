import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Anchor, Waves, AlertCircle } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import {
  getPorts, getVesselClasses, getMatrix, checkCompatibility,
  type Port, type VesselClass, type MatrixRow, type CompatibilityResult,
} from "../lib/api";

export default function Ports() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [vesselClasses, setVesselClasses] = useState<VesselClass[]>([]);
  const [matrix, setMatrix] = useState<MatrixRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedPort, setSelectedPort] = useState<number | null>(null);
  const [selectedClass, setSelectedClass] = useState<number | null>(null);
  const [cargoTonnes, setCargoTonnes] = useState<string>("75000");
  const [result, setResult] = useState<CompatibilityResult | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    Promise.all([getPorts(), getVesselClasses(), getMatrix()])
      .then(([p, vc, m]) => {
        setPorts(p);
        setVesselClasses(vc);
        setMatrix(m);
        setSelectedPort(p[0]?.id ?? null);
        setSelectedClass(vc[2]?.id ?? vc[0]?.id ?? null);
      })
      .catch(() => setLoadError("Could not load live port data from the backend."));
  }, []);

  async function runCheck() {
    if (selectedPort == null || selectedClass == null) return;
    setChecking(true);
    try {
      const tonnes = cargoTonnes ? Number(cargoTonnes) : undefined;
      const res = await checkCompatibility(selectedPort, selectedClass, tonnes);
      setResult(res);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-strong">
        Port Compatibility
      </motion.h1>

      {loadError && (
        <SpotlightCard glowColor="248,113,113">
          <p className="p-4 text-sm text-down">{loadError} Is the backend running?</p>
        </SpotlightCard>
      )}

      {/* Interactive checker */}
      <SpotlightCard>
        <div className="p-6">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
            <Anchor className="h-4 w-4 text-cyan" /> Live Compatibility Checker
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-4">
            <label className="text-sm text-muted">
              Destination port
              <select
                className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-strong"
                value={selectedPort ?? ""}
                onChange={(e) => setSelectedPort(Number(e.target.value))}
              >
                {ports.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
            <label className="text-sm text-muted">
              Vessel class
              <select
                className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2 text-sm text-strong"
                value={selectedClass ?? ""}
                onChange={(e) => setSelectedClass(Number(e.target.value))}
              >
                {vesselClasses.map((vc) => (
                  <option key={vc.id} value={vc.id}>{vc.name}</option>
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
                onClick={runCheck}
                disabled={checking || selectedPort == null}
                className="w-full rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50"
              >
                {checking ? "Checking…" : "Check compatibility"}
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {result && (
              <motion.div
                key={`${result.port_name}-${result.vessel_class_name}-${result.compatible}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-6"
              >
                <div
                  className={`flex items-center gap-3 rounded-lg border p-4 ${
                    result.compatible ? "border-up/30 bg-up/10" : "border-down/30 bg-down/10"
                  }`}
                >
                  {result.compatible ? (
                    <CheckCircle2 className="h-6 w-6 shrink-0 text-up" />
                  ) : (
                    <XCircle className="h-6 w-6 shrink-0 text-down" />
                  )}
                  <p className={`text-sm font-medium ${result.compatible ? "text-up" : "text-down"}`}>
                    {result.vessel_class_name} is {result.compatible ? "compatible with" : "NOT compatible with"} {result.port_name}
                  </p>
                </div>

                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {result.checks.map((c) => (
                    <div key={c.name} className="rounded-md border border-border-soft bg-panel-light/50 p-3 text-xs">
                      <div className="flex items-center gap-1.5 font-medium text-strong">
                        {c.passed ? <CheckCircle2 className="h-3.5 w-3.5 text-up" /> : <XCircle className="h-3.5 w-3.5 text-down" />}
                        {c.name.toUpperCase()}
                      </div>
                      <p className="mt-1 text-muted">{c.detail}</p>
                    </div>
                  ))}
                </div>

                {result.tidal_plan && (
                  <div className="mt-3 flex items-start gap-3 rounded-md border border-amber/30 bg-amber/10 p-3 text-xs">
                    <Waves className="h-4 w-4 shrink-0 text-amber" />
                    <p className="text-amber">
                      Tidal loading plan: {result.tidal_plan.cycles_required} cycles ×{" "}
                      {result.tidal_plan.tonnes_per_cycle.toLocaleString()}t/cycle ≈{" "}
                      <span className="font-semibold">{result.tidal_plan.days_required} days</span>
                      {result.tidal_plan.max_vessels_per_tide && ` (max ${result.tidal_plan.max_vessels_per_tide} vessels/tide)`}
                    </p>
                  </div>
                )}

                {result.notes.map((n, i) => (
                  <div key={i} className="mt-2 flex items-start gap-2 text-xs text-muted">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {n}
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </SpotlightCard>

      {/* Live matrix */}
      <SpotlightCard glowColor="203,213,225">
        <div className="overflow-x-auto p-2">
          <table className="min-w-full divide-y divide-border-soft text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-medium">Port</th>
                {vesselClasses.map((vc) => (
                  <th key={vc.id} className="px-4 py-3 font-medium">{vc.name}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border-soft/60">
              {matrix.map((row) => (
                <tr key={row.port_id} className="transition-colors hover:bg-panel-light/60">
                  <td className="px-4 py-3 font-medium text-strong">{row.port}</td>
                  {vesselClasses.map((vc) => (
                    <td key={vc.id} className="px-4 py-3">
                      {row.vessel_classes[vc.name] ? (
                        <CheckCircle2 className="h-4 w-4 text-up" />
                      ) : (
                        <XCircle className="h-4 w-4 text-down" />
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SpotlightCard>
      <p className="text-xs text-muted">
        Live from the Port–Vessel Compatibility Engine (Section 7) — draft/LOA/beam checked against each port's real
        researched constraints, not hardcoded.
      </p>
    </div>
  );
}
