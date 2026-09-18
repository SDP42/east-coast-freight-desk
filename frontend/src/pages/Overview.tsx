import { motion } from "framer-motion";
import { Anchor, Globe2, Ship, Sparkles } from "lucide-react";
import HealthBadge from "../components/HealthBadge";
import SpotlightCard from "../components/SpotlightCard";
import AnimatedCounter from "../components/AnimatedCounter";

const stats = [
  { label: "East Coast ports modeled", value: 7, icon: Anchor },
  { label: "Origin countries tracked", value: 5, icon: Globe2 },
  { label: "Vessel classes", value: 4, icon: Ship },
  { label: "Differentiating features", value: 18, suffix: "+", icon: Sparkles },
];

export default function Overview() {
  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-wrap items-center justify-between gap-3"
      >
        <div>
          <p className="text-xs uppercase tracking-widest text-cyan/70">Freight Intelligence Desk</p>
          <h1 className="mt-1 bg-gradient-to-r from-white via-ice to-cyan bg-clip-text text-3xl font-bold text-transparent">
            East Coast Coal Chartering — Overview
          </h1>
        </div>
        <HealthBadge />
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.4 }}
        className="max-w-3xl text-sm leading-relaxed text-muted"
      >
        AI/ML-driven freight forecasting and dry bulk vessel chartering recommendation platform
        for coal procurement to India's East Coast ports, sourced from Australia, the US,
        Mozambique, Russia and Indonesia. Built against SAIL's stated objective: move from
        single spot fixtures to structured short/medium-term voyage contracts.
      </motion.p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ label, value, suffix, icon: Icon }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.06, duration: 0.35 }}
          >
            <SpotlightCard className="h-full">
              <div className="p-5">
                <Icon className="h-4 w-4 text-cyan" strokeWidth={1.75} />
                <p className="mt-3 text-2xl font-bold text-white">
                  <AnimatedCounter value={value} suffix={suffix ?? ""} />
                </p>
                <p className="mt-1 text-xs text-muted">{label}</p>
              </div>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>

      <SpotlightCard>
        <div className="p-6">
          <h2 className="text-sm font-semibold text-white">Build status</h2>
          <p className="mt-1 text-sm text-muted">
            See <code className="rounded bg-black/40 px-1.5 py-0.5 text-cyan">SECTIONS.md</code> in the
            project root for the full running build log across all 16 implementation sections, and{" "}
            <code className="rounded bg-black/40 px-1.5 py-0.5 text-cyan">FEATURES.md</code> for the
            baseline-vs-differentiating feature split.
          </p>
        </div>
      </SpotlightCard>
    </div>
  );
}
