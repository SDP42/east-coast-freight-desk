import { motion } from "framer-motion";
import ComingSoon from "../components/ComingSoon";
import SpotlightCard from "../components/SpotlightCard";

// Seeded from our own research (Section 3.5 of the compendium) — real documented
// events, wired to the live model in Section 9.
const events = [
  { title: "Red Sea / Suez rerouting", region: "Suez Canal", category: "Geopolitical", period: "2023–2024" },
  { title: "Panama Canal drought draft restriction", region: "Panama Canal", category: "Hydrological", period: "2023–2024" },
  { title: "Cyclone Koji — Dalrymple Bay closure", region: "Queensland, Australia", category: "Weather", period: "Jan 2026" },
  { title: "EU ban on Russian coal — trade redirection", region: "Russia / Asia", category: "Sanctions", period: "2022–2024" },
];

export default function Risk() {
  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-white">
        Risk &amp; Disruptions
      </motion.h1>
      <ComingSoon title="Composite Route Risk Score & early-warning feed" section="Section 9" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {events.map((e, i) => (
          <motion.div key={e.title} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
            <SpotlightCard glowColor="248,113,113">
              <div className="p-4">
                <p className="text-xs uppercase tracking-wide text-muted">
                  {e.category} · {e.period}
                </p>
                <p className="mt-1 text-sm font-medium text-white">{e.title}</p>
                <p className="mt-1 text-xs text-muted">{e.region}</p>
              </div>
            </SpotlightCard>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
