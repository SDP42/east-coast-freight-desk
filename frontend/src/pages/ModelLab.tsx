import { useEffect, useState } from "react";
import Loading from "../components/Loading";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, Area } from "recharts";
import { Brain } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { PageHeader, Stat, errText, Fine } from "../components/ui";
import { api } from "../lib/api";
import { px } from "../lib/scale";

interface Test { horizon_months: number; origins: number; test_from: string; test_to: string; models: Record<string, { mae_usd_per_t: number; mape_pct: number; p_vs_naive: number | null }> }
interface Cur {
  data_through: string; trained_at: string; inputs?: string[]; gulf_rate_history: { month: string; usd_per_t: number }[];
  gulf_rate_forecast: { last_month: string; last_value: number; method: string; path: { month: string; forecast: number; low: number; high: number }[] };
  forecast_tests: Test[]; deep_learning: { gru_mae_usd_per_t: number; naive_mae_usd_per_t: number; p_vs_naive: number; origins: number; model: string; note: string } | null; verdicts: string[]; caveat: string;
}
interface Proof { live_refit: { mae: Record<string, number>; timings_seconds: { total: number; models_fitted: number }; window: { from: string; to: string }; note: string }; artifacts: { file: string; bytes: number; sha256: string }[]; serving: { result: string; how: string; live: boolean }[] }

export default function ModelLab() {
  const [c, setC] = useState<Cur | null>(null);
  const [proof, setProof] = useState<Proof | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get<Cur>("/lab/current").then((r) => setC(r.data)).catch((e) => setErr(errText(e)));
    api.get<Proof>("/lab/proof/OCEAN_GULF_JAPAN").then((r) => setProof(r.data)).catch(() => undefined);
  }, []);
  if (err) return <p className="text-sm text-muted">{err}</p>;
  if (!c) return <Loading label="Loading the models" block />;
  const t1 = c.forecast_tests[0];
  const board = Object.entries(t1.models).map(([model, v]) => ({ model, mae: v.mae_usd_per_t, p: v.p_vs_naive })).sort((a, b) => a.mae - b.mae);
  const path = [...c.gulf_rate_history.slice(-36).map((h) => ({ m: h.month.slice(0, 7), actual: h.usd_per_t })), ...c.gulf_rate_forecast.path.map((p) => ({ m: p.month.slice(0, 7), forecast: p.forecast, band: [p.low, p.high] as [number, number] }))];
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader title="Model lab" subtitle="Forecast models on public data, tested against 'no change'." />
      <SpotlightCard>
        <div className="space-y-4 p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-100"><Brain className="h-5 w-5 text-violet-700" /></div>
            <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-strong">Verdict</p><ul className="mt-1 space-y-1 text-sm leading-relaxed text-body">{c.verdicts.map((v) => <li key={v}>• {v}</li>)}</ul></div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Data through" value={c.data_through} /><Stat label="Forecasts tested" value={t1.origins} /><Stat label="Best 1-month MAE" value={`$${board[0].mae}/t`} tone="up" /><Stat label="No-change MAE" value={`$${t1.models.naive.mae_usd_per_t}/t`} />
          </div>
        </div>
      </SpotlightCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">1-month forecast error, US$/t (lower is better)</h2>
            <div className="mt-3 h-72"><ResponsiveContainer><BarChart data={board} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" horizontal={false} /><XAxis type="number" tick={{ fontSize: px(11), fill: "#64748b" }} /><YAxis type="category" dataKey="model" tick={{ fontSize: px(11), fill: "#334155" }} width={px(110)} />
              <Tooltip /><Bar dataKey="mae" radius={4} isAnimationActive={false}>{board.map((b) => <Cell key={b.model} fill={b.model === "naive" ? "#94a3b8" : b.p !== null && b.p < 0.05 ? (b.mae > t1.models.naive.mae_usd_per_t ? "#dc2626" : "#0e7490") : "#7c3aed"} />)}</Bar>
            </BarChart></ResponsiveContainer></div>
            <p className="mt-2 text-xs text-muted">Teal: significantly better than no-change (Wilcoxon, p under 0.05); red: significantly worse. Eight models are compared, so a p just under 0.05 needs a multiple-testing correction (see the verdict). {t1.test_from} to {t1.test_to}.</p>
          </div>
        </SpotlightCard>
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Rate history and 6-month ARIMA path</h2>
            <div className="mt-3 h-72"><ResponsiveContainer><ComposedChart data={path}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" /><XAxis dataKey="m" tick={{ fontSize: px(10), fill: "#64748b" }} interval={5} /><YAxis tick={{ fontSize: px(11), fill: "#64748b" }} domain={["auto", "auto"]} /><Tooltip />
              <Area dataKey="band" stroke="none" fill="#0e7490" fillOpacity={0.12} isAnimationActive={false} /><Line dataKey="actual" stroke="#0b2545" dot={false} isAnimationActive={false} /><Line dataKey="forecast" stroke="#0e7490" strokeDasharray="5 3" dot={false} isAnimationActive={false} />
            </ComposedChart></ResponsiveContainer></div>
            <Fine>{c.gulf_rate_forecast.method}. US Gulf to Japan grain ocean rate, US$ per tonne.</Fine>
          </div>
        </SpotlightCard>
      </div>

      {c.deep_learning && <SpotlightCard><div className="p-6"><h2 className="text-sm font-semibold text-strong">Deep learning</h2><p className="mt-1 text-sm text-body">{c.deep_learning.model}: MAE ${c.deep_learning.gru_mae_usd_per_t}/t against ${c.deep_learning.naive_mae_usd_per_t}/t for no change over {c.deep_learning.origins} monthly forecasts (p = {c.deep_learning.p_vs_naive}). {c.deep_learning.note}</p></div></SpotlightCard>}

      {proof && (
        <SpotlightCard><div className="p-6">
          <h2 className="text-sm font-semibold text-strong">Proof the models are real</h2>
          <p className="mt-1 text-sm text-body">A live refit just ran {proof.live_refit.timings_seconds.models_fitted} model fits in {proof.live_refit.timings_seconds.total} s (windows {proof.live_refit.window.from} to {proof.live_refit.window.to}). MAE: {Object.entries(proof.live_refit.mae).map(([k, v]) => `${k} ${v}`).join(" · ")}.</p>
          <table className="mt-3 w-full text-left text-xs"><thead className="text-muted"><tr><th className="py-1">Result</th><th>How it is produced</th></tr></thead><tbody>{proof.serving.map((s) => <tr key={s.result} className="border-t border-border-soft"><td className="py-1.5 pr-3 font-medium text-strong">{s.result}</td><td className="text-body">{s.how}</td></tr>)}</tbody></table>
          {proof.artifacts.length > 0 && <p className="mt-3 text-xs text-muted">Saved artifacts: {proof.artifacts.map((a) => `${a.file} (${a.sha256})`).join(", ")}.</p>}
        </div></SpotlightCard>
      )}
      <Fine>{c.caveat} Inputs: {(c.inputs ?? []).join(", ")}. Trained {c.trained_at}.</Fine>
    </div>
  );
}
