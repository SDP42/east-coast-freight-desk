import { useEffect, useMemo, useState } from "react";
import Loading from "../components/Loading";
import { px } from "../lib/scale";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { motion } from "framer-motion";
import { Brain, CheckCircle2, CircleSlash, LineChart as LineChartIcon } from "lucide-react";
import MultiHorizon from "../components/MultiHorizon";
import SpotlightCard from "../components/SpotlightCard";
import { getEnsemble, getForecast, getHistory, type EnsembleResult, type ForecastResult, type HistoryPoint } from "../lib/api";

const INDICES = [
  { key: "OCEAN_GULF_JAPAN", label: "Grain ocean rate, US Gulf to Japan" },
  { key: "OCEAN_PNW_JAPAN", label: "Grain ocean rate, US Pacific NW to Japan" },
];
const HORIZONS = [1, 3, 6, 12];  // months

const prettyFeature = (f: string) =>
  f.replace("exog_", "").replace(/_/g, " ").replace("coal ppi", "US coal price index").replace("deepsea ppi", "deep-sea freight index").replace("brent", "Brent crude").replace("inr", "rupee").replace("dxy", "US dollar index");

export default function Forecast() {
  const [indexKey, setIndexKey] = useState("OCEAN_GULF_JAPAN");
  const [horizon, setHorizon] = useState(3);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [forecast, setForecast] = useState<ForecastResult | null>(null);
  const [ensemble, setEnsemble] = useState<EnsembleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [ensembleLoading, setEnsembleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setEnsemble(null);
    Promise.all([getHistory(indexKey, 60), getForecast(indexKey, horizon)])
      .then(([h, f]) => {
        if (cancelled) return;
        setHistory(h);
        setForecast(f);
      })
      .catch(() => !cancelled && setError("Could not load the forecast — is the backend running?"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [indexKey, horizon]);

  async function runEnsemble() {
    setEnsembleLoading(true);
    try {
      setEnsemble(await getEnsemble(indexKey, Math.min(horizon, 12)));
    } catch {
      setError("The ensemble run failed or timed out.");
    } finally {
      setEnsembleLoading(false);
    }
  }

  const chartData = useMemo(() => {
    if (!forecast || history.length === 0) return [];
    const lastActual = history[history.length - 1];
    const hybridByDate = new Map(ensemble?.forecast.map((p) => [p.date, p.hybrid_value]));
    const rows: Record<string, number | string | number[] | undefined>[] = history.map((p) => ({ date: p.date, actual: p.value }));
    // Start the forecast line at the last real point so the two lines join.
    rows[rows.length - 1] = { ...rows[rows.length - 1], forecast: lastActual.value, hybrid: ensemble ? lastActual.value : undefined };
    forecast.forecast.forEach((p) =>
      rows.push({ date: p.date, forecast: p.value, band: [p.lower_ci, p.upper_ci], hybrid: hybridByDate.get(p.date) }),
    );
    return rows;
  }, [history, forecast, ensemble]);

  const lastActual = history[history.length - 1]?.value;
  const endForecast = forecast?.forecast[forecast.forecast.length - 1];
  const moveInfo = lastActual && endForecast ? ((endForecast.value - lastActual) / lastActual) * 100 : null;
  const maxShap = ensemble ? Math.max(...ensemble.top_features.map((f) => f.mean_abs_shap)) : 1;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-strong">Freight Forecast</h1>
          <p className="mt-1 text-xs text-muted">Real ARIMA model fit on the ingested series, with a 95% confidence band and walk-forward backtest.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {INDICES.map((i) => (
            <button key={i.key} onClick={() => setIndexKey(i.key)} className={`rounded-md border px-3 py-1.5 text-xs ${indexKey === i.key ? "border-cyan/50 bg-cyan/10 text-cyan" : "border-border-soft bg-panel-light text-muted hover:text-strong"}`}>
              {i.key}
            </button>
          ))}
          <span className="mx-1 w-px bg-border-soft" />
          {HORIZONS.map((h) => (
            <button key={h} onClick={() => setHorizon(h)} className={`rounded-md border px-3 py-1.5 text-xs ${horizon === h ? "border-amber/50 bg-amber/10 text-amber" : "border-border-soft bg-panel-light text-muted hover:text-strong"}`}>
              {h} mo
            </button>
          ))}
        </div>
      </motion.div>

      {error && <p className="text-sm text-down">{error}</p>}

      <SpotlightCard>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
              <LineChartIcon className="h-4 w-4 text-cyan" /> {INDICES.find((i) => i.key === indexKey)?.label}: last 60 months and {horizon}-month forecast
            </h2>
            {moveInfo != null && (
              <span className={`text-sm font-semibold ${moveInfo >= 0 ? "text-up" : "text-down"}`}>
                {moveInfo >= 0 ? "▲" : "▼"} {Math.abs(moveInfo).toFixed(1)}% projected
              </span>
            )}
          </div>
          {loading ? (
            <div className="flex h-72 items-center justify-center"><Loading label="Fitting the model" pattern="orbit" /></div>
          ) : (
            <div className="mt-4">
              <ResponsiveContainer width="100%" height={px(320)}>
                <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="date" tick={{ fontSize: px(10), fill: "#64748b" }} tickLine={false} axisLine={{ stroke: "#dbe4ee" }} minTickGap={40} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: px(10), fill: "#64748b" }} tickLine={false} axisLine={false} width={px(48)} />
                  <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #dbe4ee", borderRadius: 8, fontSize: px(12) }} labelStyle={{ color: "#64748b" }} />
                  <Area dataKey="band" stroke="none" fill="#d97706" fillOpacity={0.15} isAnimationActive={false} name="95% band" />
                  <Line dataKey="actual" stroke="#0e7490" strokeWidth={2} dot={false} isAnimationActive={false} name="Actual" />
                  <Line dataKey="forecast" stroke="#d97706" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} name="ARIMA forecast" />
                  {ensemble && <Line dataKey="hybrid" stroke="#7c3aed" strokeWidth={2} dot={false} isAnimationActive={false} name="Hybrid (ARIMA+XGBoost)" />}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </SpotlightCard>

      {forecast && !loading && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {[
            { label: "Backtest MAPE", value: `${forecast.backtest_mean_mape.toFixed(2)}%`, hint: "5 walk-forward splits" },
            { label: "Backtest RMSE", value: forecast.backtest_mean_rmse.toFixed(1), hint: "index points" },
            { label: "Backtest MAE", value: forecast.backtest_mean_mae.toFixed(1), hint: "index points" },
            { label: "ARIMA order", value: `(${forecast.order.join(",")})`, hint: "chosen by AIC" },
            { label: "Stationary", value: forecast.is_stationary ? "Yes" : "No", hint: `ADF p = ${forecast.adf_pvalue}` },
          ].map((m) => (
            <SpotlightCard key={m.label}>
              <div className="p-4">
                <p className="text-[11px] uppercase tracking-wide text-muted">{m.label}</p>
                <p className="mt-1 text-xl font-bold text-strong">{m.value}</p>
                <p className="text-[10px] text-muted">{m.hint}</p>
              </div>
            </SpotlightCard>
          ))}
        </div>
      )}

      <SpotlightCard glowColor="167,139,250">
        <div className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
                <Brain className="h-4 w-4 text-violet-600" /> Ensemble and explainability
              </h2>
              <p className="mt-1 text-xs text-muted">
                Adds XGBoost (with S&amp;P 500, dollar index and coal prices as features), blends the two by inverse error, tests the
                improvement statistically, and shows what drives the forecast. Takes about 12 seconds.
              </p>
            </div>
            <button onClick={runEnsemble} disabled={ensembleLoading} className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-violet-700 disabled:opacity-50">
              {ensembleLoading ? "Training models…" : ensemble ? "Re-run" : "Run ensemble"}
            </button>
          </div>

          {ensemble && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-muted">
                      <th className="py-2">Model</th><th>RMSE</th><th>MAE</th><th>MAPE</th><th>Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-soft/60 tabular-nums">
                    {[
                      { name: "ARIMA", m: ensemble.arima_metrics, w: ensemble.weights.arima },
                      { name: "XGBoost", m: ensemble.xgb_metrics, w: ensemble.weights.xgb },
                      { name: "Hybrid", m: ensemble.hybrid_metrics, w: null },
                    ].map((r) => (
                      <tr key={r.name} className={r.name === "Hybrid" ? "text-violet-700" : "text-body"}>
                        <td className="py-2 font-medium">{r.name}</td>
                        <td>{r.m.rmse.toFixed(1)}</td><td>{r.m.mae.toFixed(1)}</td><td>{r.m.mape.toFixed(2)}%</td>
                        <td>{r.w != null ? `${(r.w * 100).toFixed(0)}%` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-4 space-y-2 text-xs">
                  {[
                    { label: "Hybrid vs ARIMA", s: ensemble.hybrid_vs_arima },
                    { label: "Hybrid vs XGBoost", s: ensemble.hybrid_vs_xgb },
                  ].map(({ label, s }) => (
                    <div key={label} className="flex items-center gap-2">
                      {s.significant_at_05 ? <CheckCircle2 className="h-4 w-4 shrink-0 text-up" /> : <CircleSlash className="h-4 w-4 shrink-0 text-muted" />}
                      <span className="text-body">
                        {label}: Wilcoxon p = {s.p_value < 0.0001 ? s.p_value.toExponential(1) : s.p_value.toFixed(4)}{" "}
                        <span className={s.significant_at_05 ? "text-up" : "text-muted"}>{s.significant_at_05 ? "(significant)" : "(not significant)"}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-[11px] uppercase tracking-wide text-muted">What drives the XGBoost forecast (SHAP)</p>
                <div className="space-y-1.5">
                  {ensemble.top_features.map((f) => (
                    <div key={f.feature} className="flex items-center gap-2 text-xs">
                      <span className="w-32 shrink-0 truncate text-body">{prettyFeature(f.feature)}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-panel-light">
                        <div className="h-full rounded-full bg-violet-600" style={{ width: `${Math.max(2, (f.mean_abs_shap / maxShap) * 100)}%` }} />
                      </div>
                      <span className="w-12 text-right tabular-nums text-muted">{f.mean_abs_shap.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] text-muted">
                  Last month's value dominates, which is expected for a highly autocorrelated monthly rate; the smaller bars show what the
                  macro and commodity features add on top.
                </p>
              </div>
            </motion.div>
          )}
        </div>
      </SpotlightCard>

      {forecast && !loading && (
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Backtest, split by split</h2>
            <p className="mt-1 text-xs text-muted">Each row retrains on everything up to the date shown and forecasts the next {horizon} month(s). Steady error across rows is what a trustworthy model looks like.</p>
            <table className="mt-3 w-full text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Split</th><th>Trained to</th><th>RMSE</th><th>MAE</th><th>MAPE</th></tr></thead>
              <tbody>{forecast.backtest_splits.map((b) => (
                <tr key={b.split_index} className="border-t border-border-soft"><td className="py-1.5">#{b.split_index + 1}</td><td>{b.train_end}</td><td>{b.rmse.toFixed(1)}</td><td>{b.mae.toFixed(1)}</td><td className={b.mape > forecast.backtest_mean_mape * 1.5 ? "font-semibold text-down" : ""}>{b.mape.toFixed(2)}%</td></tr>
              ))}</tbody>
            </table>
          </div>
        </SpotlightCard>
      )}
      <MultiHorizon indexName={indexKey} />
    </div>
  );
}
