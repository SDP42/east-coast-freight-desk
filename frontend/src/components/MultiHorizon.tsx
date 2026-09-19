import { useEffect, useState } from "react";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import SpotlightCard from "./SpotlightCard";
import { Note } from "./ui";
import { api } from "../lib/api";

interface Res { index_name: string; last_date: string; last_value: number; horizons: { horizon: number; value: number; change_pct: number; lower: number; upper: number }[]; note: string }

/** 7 / 14 / 30 / 60 / 90-day outlook side by side, with the band widening. */
export default function MultiHorizon({ indexName }: { indexName: string }) {
  const [res, setRes] = useState<Res | null>(null);
  useEffect(() => { setRes(null); api.get<Res>(`/forecast-multi/${indexName}`).then((r) => setRes(r.data)).catch(() => setRes(null)); }, [indexName]);
  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="text-sm font-semibold text-strong">Multi-horizon outlook</h2>
        <p className="mt-1 text-xs text-muted">The same model at five horizons. Watch the band: the further out, the less the direction means.</p>
        {!res ? <p className="mt-4 text-sm text-muted">Fitting…</p> : (
          <div className="mt-4 space-y-4">
            <div className="h-56">
              <ResponsiveContainer>
                <ComposedChart data={res.horizons.map((h) => ({ ...h, name: `${h.horizon}d`, range: [h.lower, h.upper] }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#64748b" }} width={48} />
                  <Tooltip />
                  <Bar isAnimationActive={false} dataKey="range" fill="#d97706" fillOpacity={0.25} name="95% band" radius={4} />
                  <Line dataKey="value" stroke="#0e7490" strokeWidth={2} name="Forecast" isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <table className="w-full text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Horizon</th><th>Forecast</th><th>Change vs {res.last_date}</th><th>95% band</th><th>Band width</th></tr></thead>
              <tbody>{res.horizons.map((h) => (
                <tr key={h.horizon} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{h.horizon} days</td><td>{h.value.toLocaleString()}</td><td className={h.change_pct >= 0 ? "text-down" : "text-up"}>{h.change_pct > 0 ? "+" : ""}{h.change_pct}%</td><td>{h.lower.toLocaleString()} to {h.upper.toLocaleString()}</td><td className="text-muted">±{(((h.upper - h.lower) / 2 / res.last_value) * 100).toFixed(0)}%</td></tr>
              ))}</tbody>
            </table>
            <Note>{res.note}</Note>
          </div>
        )}
      </div>
    </SpotlightCard>
  );
}
