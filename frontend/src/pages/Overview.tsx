import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Anchor, ArrowUpRight, Database, Globe2, Ship } from "lucide-react";
import BriefingCard from "../components/BriefingCard";
import HealthBadge from "../components/HealthBadge";
import SpotlightCard from "../components/SpotlightCard";
import AnimatedCounter from "../components/AnimatedCounter";
import LiveChart from "../components/LiveChart";
import { useAuth } from "../lib/auth";
import { PERSONA_LABEL, personaView, routeAllowed } from "../lib/personas";

const stats = [
  { label: "East Coast ports modelled", value: 7, icon: Anchor },
  { label: "Origin countries compared", value: 5, icon: Globe2 },
  { label: "Vessel classes", value: 4, icon: Ship },
  { label: "Real data series", value: 12, icon: Database },
];

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Overview() {
  const { user, can } = useAuth();
  const view = personaView(user?.persona ?? user?.role);
  const actions = view.quickActions.filter((a) => routeAllowed(a.to, can));
  const firstName = (user?.full_name || user?.email || "").split(/[ @]/)[0];

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest" style={{ color: `rgb(${view.accent})` }}>
            {user?.role_label ?? PERSONA_LABEL[user?.role ?? ""] ?? "Freight desk"} · level {user?.level ?? 0}
          </p>
          <h1 className="mt-1 bg-gradient-to-r from-strong via-body to-cyan bg-clip-text text-3xl font-bold text-transparent">
            {greeting()}, {firstName}
          </h1>
          <p className="mt-1 text-sm text-muted">{user?.role_summary || view.tagline}</p>
        </div>
        <HealthBadge />
      </motion.div>

      <div>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Start here</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {actions.map((a, i) => (
            <motion.div key={a.to + a.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 * i }}>
              <Link to={a.to}>
                <SpotlightCard glowColor={view.accent} className="h-full transition hover:border-cyan/30">
                  <div className="p-5">
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-semibold text-strong">{a.label}</p>
                      <ArrowUpRight className="h-4 w-4 text-muted" />
                    </div>
                    <p className="mt-2 text-xs text-muted">{a.hint}</p>
                  </div>
                </SpotlightCard>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      <BriefingCard />

      {can("market:read") && <SpotlightCard>
        <div className="p-6">
          <LiveChart indexName="BPI" label="Baltic Panamax Index (BPI)" height={260} />
        </div>
      </SpotlightCard>}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map(({ label, value, icon: Icon }, i) => (
          <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.06 }}>
            <SpotlightCard className="h-full">
              <div className="p-5">
                <Icon className="h-4 w-4 text-cyan" strokeWidth={1.75} />
                <p className="mt-3 text-2xl font-bold text-strong"><AnimatedCounter value={value} /></p>
                <p className="mt-1 text-xs text-muted">{label}</p>
              </div>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
