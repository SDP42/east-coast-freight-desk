import { useCallback, useEffect, useState } from "react";
import { px } from "../lib/scale";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RefreshCw } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader, Stat, btnCls, errText } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Report {
  index_name: string; data_through: string; frozen_model_trained_through: string; reference_mape: number; recent_mape: number; error_ratio: number; mann_whitney_p: number;
  return_psi: number; model_drift: boolean; data_drift: boolean; status: string; thresholds: { error_ratio: number; p_value: number; psi: number }; method: string; last_retrained: string | null;
  rolling_mape: { date: string; mape_30d: number }[];
  history: { id: number; trained_at: string; trigger: string; order: string; train_rows: number; train_end: string; holdout_mape: number | null; drift_before: boolean }[];
}

export default function Monitor() {
  const { can } = useAuth();
  const [idx, setIdx] = useState("BPI");
  const [rep, setRep] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const load = useCallback(async (i: string) => { setErr(""); try { setRep((await api.get<Report>(`/monitor/${i}`)).data); } catch (e) { setErr(errText(e)); } }, []);
  useEffect(() => { load(idx); }, [idx, load]);
  async function retrain() { setBusy(true); try { await api.post(`/monitor/${idx}/retrain`); await load(idx); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } }
  const drift = rep?.status === "drift";
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Model monitor" subtitle="Is the forecast model still behaving as it did when it was trained? Frozen parameters are scored on newer data; drift is flagged and the model can be retrained." />
      <div className="flex items-center gap-3">
        <select value={idx} onChange={(e) => setIdx(e.target.value)} className="rounded-lg border border-border-soft bg-white px-3 py-2 text-sm text-strong">{["BCI", "BPI", "BSI", "BHSI"].map((i) => <option key={i}>{i}</option>)}</select>
        {can("monitor:retrain") && <button onClick={retrain} disabled={busy} className={btnCls + " flex items-center gap-2"}><RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} /> {busy ? "Retraining…" : "Retrain now"}</button>}
      </div>
      {err && <p className="text-xs text-down">{err}</p>}
      {rep && (
        <>
          <div className={`rounded-2xl border px-4 py-3 ${drift ? "border-amber/40 bg-amber/10" : "border-up/30 bg-up/10"}`}>
            <p className={`text-sm font-semibold ${drift ? "text-amber" : "text-up"}`}>
              {rep.model_drift ? "Model drift flagged: forecast errors have risen significantly." : rep.data_drift ? "Data drift flagged: daily moves are distributed differently from the past year, but forecast errors are still in line." : "Stable: forecast errors and daily moves match the past year."}
            </p>
            <p className="text-xs text-body">Data through {rep.data_through}. Frozen model trained through {rep.frozen_model_trained_through}.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Stat label="Reference error (MAPE)" value={`${rep.reference_mape}%`} />
            <Stat label="Recent error (MAPE)" value={`${rep.recent_mape}%`} tone={rep.model_drift ? "down" : undefined} />
            <Stat label="Error ratio" value={`${rep.error_ratio}×`} tone={rep.error_ratio > rep.thresholds.error_ratio ? "down" : "up"} />
            <Stat label="Mann-Whitney p" value={rep.mann_whitney_p} />
            <Stat label="Return PSI" value={rep.return_psi} tone={rep.return_psi > rep.thresholds.psi ? "warn" : "up"} />
          </div>
          <SpotlightCard>
            <div className="p-6">
              <h2 className="text-sm font-semibold text-strong">Rolling 30-day one-step error</h2>
              <div className="mt-3 h-56">
                <ResponsiveContainer>
                  <LineChart data={rep.rolling_mape}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                    <XAxis dataKey="date" tick={{ fontSize: px(10), fill: "#64748b" }} minTickGap={50} />
                    <YAxis tick={{ fontSize: px(11), fill: "#64748b" }} width={px(40)} unit="%" />
                    <ReferenceLine y={rep.reference_mape} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: "reference", fontSize: px(10), fill: "#64748b", position: "insideTopLeft" }} />
                    <Tooltip formatter={(v) => [`${v}%`, "MAPE (30d)"]} />
                    <Line dataKey="mape_30d" stroke="#0e7490" strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3"><Note>{rep.method} Thresholds: error ratio above {rep.thresholds.error_ratio} with p below {rep.thresholds.p_value}, or PSI above {rep.thresholds.psi} (a common rule of thumb).</Note></div>
            </div>
          </SpotlightCard>
          <SpotlightCard>
            <div className="p-6">
              <h2 className="text-sm font-semibold text-strong">Retraining history</h2>
              {rep.history.length === 0 ? <p className="mt-2 text-sm text-muted">No retraining runs recorded yet.</p> : (
                <table className="mt-3 w-full text-left text-sm">
                  <thead><tr className="text-xs text-muted"><th className="py-1">Run</th><th>When</th><th>Trigger</th><th>Order</th><th>Rows</th><th>Trained to</th><th>30-day holdout</th><th>Drift before</th></tr></thead>
                  <tbody>{rep.history.map((h) => <tr key={h.id} className="border-t border-border-soft"><td className="py-1.5">#{h.id}</td><td>{h.trained_at.slice(0, 16)}</td><td>{h.trigger}</td><td>{h.order}</td><td>{h.train_rows}</td><td>{h.train_end}</td><td>{h.holdout_mape !== null ? `${h.holdout_mape}%` : "n/a"}</td><td>{h.drift_before ? "yes" : "no"}</td></tr>)}</tbody>
                </table>
              )}
              <div className="mt-3"><Note kind="warn">The freight data ends on {rep.data_through} and is not refreshed automatically, so retraining currently reproduces the same model; the pipeline (drift check, refit, cache reset, run record) is what matters once a live feed is connected.</Note></div>
            </div>
          </SpotlightCard>
        </>
      )}
    </div>
  );
}
