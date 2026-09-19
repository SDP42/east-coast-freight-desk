import { useEffect, useState } from "react";
import Loading from "../components/Loading";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Brain } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader, Stat } from "../components/ui";
import { api } from "../lib/api";
import { px } from "../lib/scale";

interface Row { model: string; mae: number; rmse: number; mape: number; parameters?: number; vs_arima_p?: number; train_seconds?: number }
interface Lab {
  index: string; horizon_days: number; paired_forecasts: number; splits: number; lookback_days: number; seeds_per_model: number; verdict: string; served_models: string[]; trained_at: string; note: string;
  weather_experiment: { verdict: string; pooled_p_weather_better: number | null; note: string; ports: { port: string; mae_naive: number; mae_calls_only: number; mae_with_weather: number; weather_gain_pct: number }[] } | null;
  data: { rows: number; from: string; to: string }; leaderboard: Row[]; curves: Record<string, { train: number[]; val: number[] }>;
}
interface Deep { dates: string[]; last_value: number; last_date: string; forecasts: Record<string, number[]>; note: string }
interface Arima { forecast: { date: string; value: number }[] }
const DEEP = ["LSTM", "GRU", "TCN", "Transformer", "Deep ensemble (mean of 4)"];

export default function ModelLab() {
  const [lab, setLab] = useState<Lab | null>(null);
  const [deep, setDeep] = useState<Deep | null>(null);
  const [arima, setArima] = useState<Arima | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get<Lab>("/lab/models").then((r) => setLab(r.data)).catch(() => setErr("The deep-learning experiment has not been run on this deployment."));
    api.get<Deep>("/forecast-deep/BPI").then((r) => setDeep(r.data)).catch(() => undefined);
    api.get<Arima>("/forecast/BPI", { params: { horizon: 7 } }).then((r) => setArima(r.data)).catch(() => undefined);
  }, []);
  if (err) return <p className="text-sm text-muted">{err}</p>;
  if (!lab) return <Loading label="Loading the leaderboard" block />;
  const best = lab.leaderboard[0];
  const curveKeys = Object.keys(lab.curves);
  const maxLen = Math.max(...curveKeys.map((k) => lab.curves[k].val.length));
  const curveData = Array.from({ length: maxLen }, (_, i) => Object.fromEntries([["epoch", i + 1], ...curveKeys.map((k) => [k, lab.curves[k].val[i] ?? null])]));
  const pathData = deep ? deep.dates.map((d, i) => ({ d: d.slice(5), ...Object.fromEntries(Object.entries(deep.forecasts).map(([k, v]) => [k.toUpperCase(), v[i]])), ARIMA: arima?.forecast[i]?.value })) : [];
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader title="Model lab" subtitle="Deep learning against the classical models on the same forecasts. Real numbers, including where the neural networks did not clearly win." />
      <SpotlightCard>
        <div className="space-y-4 p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-100"><Brain className="h-5 w-5 text-violet-700" /></div>
            <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-strong">Verdict</p><p className="mt-1 text-sm leading-relaxed text-body">{lab.verdict}</p></div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Best model" value={<span className="text-sm">{best.model.replace(" (mean of 4)", "")}</span>} /><Stat label="Best MAE" value={best.mae} tone="up" /><Stat label="Paired forecasts" value={lab.paired_forecasts} /><Stat label="Training rows" value={lab.data.rows.toLocaleString()} />
          </div>
        </div>
      </SpotlightCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Leaderboard: mean absolute error (points, lower is better)</h2>
            <div className="mt-3 h-72">
              <ResponsiveContainer>
                <BarChart data={lab.leaderboard} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: px(11), fill: "#64748b" }} />
                  <YAxis type="category" dataKey="model" tick={{ fontSize: px(11), fill: "#334e68" }} width={px(150)} />
                  <Tooltip />
                  <Bar dataKey="mae" isAnimationActive={false} radius={[0, 6, 6, 0]}>{lab.leaderboard.map((r) => <Cell key={r.model} fill={DEEP.includes(r.model) ? "#7c3aed" : "#0e7490"} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 flex gap-4 text-[11px] text-muted"><span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-violet-600" />deep learning</span><span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-cyan" />classical</span></p>
          </div>
        </SpotlightCard>
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Training curves (validation loss, last split)</h2>
            <div className="mt-3 h-72">
              <ResponsiveContainer>
                <LineChart data={curveData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="epoch" tick={{ fontSize: px(11), fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: px(11), fill: "#64748b" }} width={px(44)} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: px(11) }} />
                  {curveKeys.map((k, i) => <Line key={k} dataKey={k} name={k.toUpperCase()} stroke={["#7c3aed", "#0e7490", "#d97706", "#dc2626"][i % 4]} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />)}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </SpotlightCard>
      </div>

      <SpotlightCard>
        <div className="overflow-x-auto p-6">
          <h2 className="text-sm font-semibold text-strong">Full table</h2>
          <table className="mt-3 w-full min-w-[640px] text-left text-sm">
            <thead><tr className="text-xs text-muted"><th className="py-1">Model</th><th>MAE</th><th>RMSE</th><th>MAPE</th><th>Parameters</th><th>vs ARIMA (p)</th><th>Train time</th></tr></thead>
            <tbody>{lab.leaderboard.map((r) => (
              <tr key={r.model} className="border-t border-border-soft">
                <td className="py-1.5 font-medium text-strong">{r.model}</td><td>{r.mae}</td><td>{r.rmse}</td><td>{r.mape}%</td><td>{r.parameters?.toLocaleString() ?? "n/a"}</td>
                <td>{r.vs_arima_p === undefined ? <span className="text-muted">baseline</span> : <span className={r.vs_arima_p < 0.05 ? "font-semibold text-up" : "text-muted"}>{r.vs_arima_p}{r.vs_arima_p < 0.05 ? " significant" : ""}</span>}</td>
                <td className="text-muted">{r.train_seconds ? `${r.train_seconds}s` : "n/a"}</td>
              </tr>
            ))}</tbody>
          </table>
          <div className="mt-3"><Note>{lab.note} Each deep model is the average of {lab.seeds_per_model} random seeds, looks back {lab.lookback_days} days at the index and four exogenous series, and is retrained at each of {lab.splits} walk-forward splits on data available at that point.</Note></div>
        </div>
      </SpotlightCard>

      {lab.weather_experiment && (
        <SpotlightCard>
          <div className="overflow-x-auto p-6">
            <h2 className="text-sm font-semibold text-strong">Does weather help predict port traffic?</h2>
            <p className="mt-1 text-sm text-body">{lab.weather_experiment.verdict} Pooled test p = {lab.weather_experiment.pooled_p_weather_better}.</p>
            <table className="mt-3 w-full min-w-[520px] text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Port</th><th>Naive</th><th>Calls only</th><th>With weather</th><th>Weather gain</th></tr></thead>
              <tbody>{lab.weather_experiment.ports.map((p) => (
                <tr key={p.port} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{p.port}</td><td>{p.mae_naive}</td><td>{p.mae_calls_only}</td><td>{p.mae_with_weather}</td><td className={p.weather_gain_pct > 0 ? "text-up" : "text-down"}>{p.weather_gain_pct > 0 ? "+" : ""}{p.weather_gain_pct}%</td></tr>
              ))}</tbody>
            </table>
            <div className="mt-3"><Note>{lab.weather_experiment.note} MAE in calls per day; a negative is worse. Weather data: Open-Meteo (CC BY 4.0).</Note></div>
          </div>
        </SpotlightCard>
      )}

      {deep && (
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Live 7-day paths from the saved deep models (served without PyTorch)</h2>
            <div className="mt-3 h-64">
              <ResponsiveContainer>
                <LineChart data={pathData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="d" tick={{ fontSize: px(11), fill: "#64748b" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: px(11), fill: "#64748b" }} width={px(48)} />
                  <Tooltip /><Legend wrapperStyle={{ fontSize: px(11) }} />
                  {Object.keys(deep.forecasts).map((k, i) => <Line key={k} dataKey={k.toUpperCase()} stroke={["#7c3aed", "#0e7490"][i % 2]} strokeWidth={2} dot={false} isAnimationActive={false} />)}
                  <Line dataKey="ARIMA" stroke="#d97706" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3"><Note>{deep.note} Last observation {deep.last_date}: {deep.last_value.toLocaleString()}.</Note></div>
          </div>
        </SpotlightCard>
      )}
    </div>
  );
}
