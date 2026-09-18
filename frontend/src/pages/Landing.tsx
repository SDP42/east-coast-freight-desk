import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Anchor, ArrowRight, Calculator, Compass, FlaskConical, Gauge, LineChart, MapPinned, ShieldAlert, Activity,
} from "lucide-react";
import OceanBackdrop from "../components/OceanBackdrop";
import TickerTape from "../components/TickerTape";
import LiveChart from "../components/LiveChart";
import SpotlightCard from "../components/SpotlightCard";
import AnimatedCounter from "../components/AnimatedCounter";
import { getPersonas, useAuth, type Persona } from "../lib/auth";
import { personaView } from "../lib/personas";

const PROBLEM_STATS = [
  { value: 94, prefix: "−", suffix: "%", label: "BDI collapse, May → Dec 2008", detail: "11,793 → 663 points in seven months" },
  { value: 91, prefix: "−", suffix: "%", label: "BDI fall, Oct 2021 → Feb 2023", detail: "5,650 → 530 points" },
  { value: 84, prefix: "~", suffix: "%", label: "of SAIL's coking coal is imported", detail: "CAG audit: 19.37 MT used, 2.45 MT domestic" },
  { value: 49.5, prefix: "", suffix: " h", decimals: 1, label: "average port turnaround, FY25", detail: "with idle time still at 16.3% of port stay" },
];

const CAPABILITIES = [
  { icon: Activity, title: "Live market boards", text: "Freight indices, coal, FX and equities by region, replayed so spikes and collapses play out on screen." },
  { icon: LineChart, title: "Forecasts with proof", text: "ARIMA and XGBoost blended by error, with confidence bands, a backtest, and a significance test you can inspect." },
  { icon: MapPinned, title: "Berth-fit engine", text: "Draft, length, beam and tidal windows for all seven East Coast ports, so nothing is chartered that cannot berth." },
  { icon: Compass, title: "Five origins, one cargo", text: "Australia, the US, Mozambique, Russia and Indonesia ranked together on cost, fit and market direction." },
  { icon: ShieldAlert, title: "Route risk scoring", text: "Disruptions, congestion and freight volatility combined into one explained score per route." },
  { icon: FlaskConical, title: "Scenario sandbox", text: "Spike freight, close a port, shut the Red Sea, and see how the best decision changes." },
  { icon: Calculator, title: "COA vs spot", text: "Simulate locking a contract against staying spot, with the savings case for finance." },
  { icon: Gauge, title: "Demurrage and idle time", text: "Price laytime overruns and rank next fixtures by how little the ship sits empty." },
];

const STEPS = [
  { n: "1", title: "Read the market", text: "See where every relevant price is heading and how violently it has moved." },
  { n: "2", title: "Compare and stress-test", text: "Rank origins for a cargo, then break the assumptions to see what survives." },
  { n: "3", title: "Decide and lock in", text: "Choose spot or a multi-voyage contract with the cost and risk in front of you." },
];

export default function Landing() {
  const { user } = useAuth();
  const [personas, setPersonas] = useState<Persona[]>([]);

  useEffect(() => {
    getPersonas().then(setPersonas).catch(() => setPersonas([]));
  }, []);

  return (
    <div className="min-h-screen text-slate-100">
      <OceanBackdrop />
      <TickerTape />

      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan/20 bg-gradient-to-br from-cyan/20 to-steel/40">
            <Anchor className="h-5 w-5 text-cyan" strokeWidth={1.75} />
          </div>
          <span className="text-sm font-semibold text-white">East Coast Freight Desk</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-muted md:flex">
          <a href="#problem" className="hover:text-white">The problem</a>
          <a href="#capabilities" className="hover:text-white">Capabilities</a>
          <a href="#personas" className="hover:text-white">Who it's for</a>
        </nav>
        <div className="flex items-center gap-2">
          {user ? (
            <Link to="/app" className="rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-navy hover:bg-cyan">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="rounded-md px-4 py-2 text-sm text-ice hover:text-white">Sign in</Link>
              <Link to="/register" className="rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-navy hover:bg-cyan">Get started</Link>
            </>
          )}
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-20 pt-10 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <p className="text-xs font-medium uppercase tracking-widest text-cyan/80">Smart India Hackathon 2026 · Coal chartering for India's East Coast</p>
          <h1 className="mt-4 bg-gradient-to-r from-white via-ice to-cyan bg-clip-text text-4xl font-bold leading-tight text-transparent sm:text-5xl">
            Stop hunting the spot market every morning.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted">
            Dry bulk freight has lost ninety percent of its value in as little as seven months. Buying coal on single spot voyages means every fixture is
            priced on whatever the market is doing that day. This desk forecasts the market, checks what each port can physically
            take, and shows when a multi-voyage contract beats spot.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={user ? "/app" : "/register"} className="flex items-center gap-2 rounded-md bg-cyan/90 px-5 py-2.5 text-sm font-medium text-navy transition hover:bg-cyan">
              {user ? "Open dashboard" : "Create an account"} <ArrowRight className="h-4 w-4" />
            </Link>
            {!user && <Link to="/login" className="rounded-md border border-border-soft px-5 py-2.5 text-sm text-ice transition hover:border-cyan/40 hover:text-white">Sign in</Link>}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15 }}>
          <SpotlightCard>
            <div className="p-5">
              <LiveChart indexName="BDI" label="Baltic Dry Index" height={230} compact />
            </div>
          </SpotlightCard>
        </motion.div>
      </section>

      <section id="problem" className="mx-auto max-w-6xl px-6 pb-20">
        <h2 className="text-2xl font-bold text-white">The problem, in numbers</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">From our research compendium, with sources cited in the full document.</p>
        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {PROBLEM_STATS.map((s) => (
            <SpotlightCard key={s.label} className="h-full">
              <div className="p-5">
                <p className="text-3xl font-bold text-white">
                  <AnimatedCounter value={s.value} prefix={s.prefix} suffix={s.suffix} decimals={s.decimals ?? 0} />
                </p>
                <p className="mt-2 text-sm text-ice/90">{s.label}</p>
                <p className="mt-1 text-xs text-muted">{s.detail}</p>
              </div>
            </SpotlightCard>
          ))}
        </div>
      </section>

      <section id="capabilities" className="mx-auto max-w-6xl px-6 pb-20">
        <h2 className="text-2xl font-bold text-white">What it does</h2>
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c, i) => (
            <motion.div key={c.title} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 4) * 0.06 }}>
              <SpotlightCard className="h-full">
                <div className="p-5">
                  <c.icon className="h-5 w-5 text-cyan" strokeWidth={1.75} />
                  <h3 className="mt-3 text-sm font-semibold text-white">{c.title}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted">{c.text}</p>
                </div>
              </SpotlightCard>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-20">
        <div className="grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="flex gap-4 rounded-xl border border-border-soft bg-panel/60 p-5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan/30 bg-cyan/10 text-sm font-semibold text-cyan">{s.n}</span>
              <div>
                <h3 className="text-sm font-semibold text-white">{s.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-muted">{s.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="personas" className="mx-auto max-w-6xl px-6 pb-24">
        <h2 className="text-2xl font-bold text-white">Built for the people in the decision</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">Pick a role when you sign up and the desk opens on the tools that role uses most.</p>
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {personas.map((p) => {
            const v = personaView(p.key);
            return (
              <SpotlightCard key={p.key} glowColor={v.accent} className="h-full">
                <div className="p-5">
                  <v.icon className="h-5 w-5" style={{ color: `rgb(${v.accent})` }} strokeWidth={1.75} />
                  <h3 className="mt-3 text-sm font-semibold text-white">{p.label}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted">{p.description}</p>
                </div>
              </SpotlightCard>
            );
          })}
        </div>
      </section>

      <footer className="border-t border-border-soft">
        <div className="mx-auto max-w-6xl px-6 py-8 text-xs leading-relaxed text-muted">
          <p>
            Prices shown are real ingested data, replayed rather than streamed live. Baltic Exchange freight indices in this build end
            in July 2019 (the live feed is a paid subscription); coal, currency and equity series run to 2024–2026. Cost figures in the
            tools are labelled illustrative estimates, not live quotes.
          </p>
          <p className="mt-3">Built for the Smart India Hackathon 2026.</p>
        </div>
      </footer>
    </div>
  );
}
