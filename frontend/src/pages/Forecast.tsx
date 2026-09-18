import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts";
import { motion } from "framer-motion";
import ComingSoon from "../components/ComingSoon";
import SpotlightCard from "../components/SpotlightCard";

// Illustrative placeholder shape only (not real BDI values) — Section 5/6 will
// replace this with live model output from the ingested Mendeley/Baltic dataset.
const placeholderSeries = Array.from({ length: 30 }, (_, i) => ({
  day: `D${i + 1}`,
  bdi: 3300 + Math.round(Math.sin(i / 4) * 250 + (Math.random() - 0.5) * 100),
}));

export default function Forecast() {
  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-white">
        Freight Forecast
      </motion.h1>
      <ComingSoon title="Multi-horizon ensemble forecast (7 / 30 / 90-day)" section="Sections 5–6" />

      <SpotlightCard>
        <div className="p-6">
          <p className="mb-4 text-xs uppercase tracking-wide text-muted">
            Placeholder chart shape — not real freight data
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={placeholderSeries}>
              <defs>
                <linearGradient id="bdiGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#232d45" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#8792a8" }} axisLine={{ stroke: "#232d45" }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#8792a8" }} domain={["auto", "auto"]} axisLine={{ stroke: "#232d45" }} tickLine={false} />
              <Tooltip contentStyle={{ background: "#131a2b", border: "1px solid #232d45", borderRadius: 8, fontSize: 12 }} labelStyle={{ color: "#8792a8" }} />
              <Area type="monotone" dataKey="bdi" stroke="#22d3ee" strokeWidth={2} fill="url(#bdiGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </SpotlightCard>
    </div>
  );
}
