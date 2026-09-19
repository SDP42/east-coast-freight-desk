import { lazy, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Anchor, ArrowRight, Calculator, Compass, FlaskConical, Gauge, LineChart, MapPinned, ShieldAlert, Activity, MessageSquareText, Ship,
} from "lucide-react";
import OceanBackdrop from "../components/OceanBackdrop";
import TickerTape from "../components/TickerTape";
import LiveChart from "../components/LiveChart";
import SpotlightCard from "../components/SpotlightCard";
import AnimatedCounter from "../components/AnimatedCounter";
import SplitText from "../components/SplitText";
import Magnet from "../components/Magnet";
import TiltCard from "../components/TiltCard";
import Marquee from "../components/Marquee";
import { HALDIA_PHASES } from "../lib/haldiaPhases";
import { getPersonas, useAuth, type Persona } from "../lib/auth";
import { getHaldiaSummary, type HaldiaSummary } from "../lib/api";
import { personaView } from "../lib/personas";

const HaldiaScene = lazy(() => import("../components/HaldiaScene"));

const PROBLEM_STATS = [
  { value: 86, prefix: "−", suffix: "%", label: "Panamax index fall, Dec 2013 → Feb 2016", detail: "2,096 → 282 points in 26 months (our data)" },
  { value: 94, prefix: "", suffix: "%", label: "of SAIL's imported coal on long-term deals", detail: "CAG audit FY17–FY23: 12 agreements, no global tender" },
  { value: 87, prefix: "~", suffix: "%", label: "of SAIL's coking coal is imported", detail: "FY24 annual report: 16.92 of 19.37 MT" },
  { value: 58.3, prefix: "", suffix: " h", decimals: 1, label: "average major-port turnaround, FY25", detail: "Ministry of Ports; Visakhapatnam 69 h, Paradip 45 h" },
];

const CAPABILITIES = [
  { icon: MessageSquareText, title: "Ask the Freight Desk", text: "Type a question in plain English. A local intent model routes it to the forecast, risk or berth engine and answers with the numbers." },
  { icon: Activity, title: "Live market boards", text: "Freight indices, coal, FX and equities by region, replayed so spikes and collapses play out on screen." },
  { icon: LineChart, title: "Forecasts with proof", text: "ARIMA and XGBoost backtested on seven years of real daily freight indices, with confidence bands and an honest significance test." },
  { icon: MapPinned, title: "Berth-fit engine", text: "Draft, length, beam and tidal windows for all seven East Coast ports, checked against real Haldia coal calls." },
  { icon: Compass, title: "Five origins, one cargo", text: "Australia, the US, Mozambique, Russia and Indonesia ranked together on cost, fit and market direction." },
  { icon: ShieldAlert, title: "Route risk scoring", text: "Disruptions, PortWatch congestion and freight volatility combined into one explained score per route." },
  { icon: FlaskConical, title: "Scenario sandbox", text: "Spike freight, close a port, shut the Red Sea, and see how the best decision changes." },
  { icon: Calculator, title: "COA vs spot", text: "Simulate locking a contract against staying spot, with the savings case for finance." },
];

const SOURCES = ["Baltic freight indices 2012–2019", "IMF PortWatch", "SMP Kolkata daily positions", "Ministry of Ports", "SAIL annual reports", "CAG audit 2025", "World Bank Pink Sheet", "FRED", "IBTrACS cyclones", "UN Comtrade"];

const STEPS = [
  { n: "1", title: "Read the market", text: "See where every relevant price is heading and how violently it has moved." },
  { n: "2", title: "Compare and stress-test", text: "Rank origins for a cargo, then break the assumptions to see what survives." },
  { n: "3", title: "Decide and lock in", text: "Choose spot or a multi-voyage contract with the cost and risk in front of you." },
];

export default function Landing() {
  const { user } = useAuth();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [phase, setPhase] = useState(0);
  const [haldia, setHaldia] = useState<HaldiaSummary | null>(null);

  useEffect(() => {
    getPersonas().then(setPersonas).catch(() => setPersonas([]));
    getHaldiaSummary().then(setHaldia).catch(() => setHaldia(null));
  }, []);

  const obs = haldia?.observed;
  const current = HALDIA_PHASES[phase] ?? HALDIA_PHASES[0];
  const btnPrimary = "flex items-center gap-2 rounded-full bg-strong px-6 py-3 text-sm font-medium text-on-accent shadow-lg shadow-slate-900/10 transition hover:bg-cyan";

  return (
    <div className="min-h-screen text-body">
      <OceanBackdrop />
      <TickerTape />

      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-strong">
            <Anchor className="h-5 w-5 text-white" strokeWidth={1.75} />
          </div>
          <span className="text-sm font-semibold text-strong">East Coast Freight Desk</span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-muted md:flex">
          <a href="#haldia" className="hover:text-strong">Haldia</a>
          <a href="#problem" className="hover:text-strong">The problem</a>
          <a href="#capabilities" className="hover:text-strong">Capabilities</a>
          <a href="#personas" className="hover:text-strong">Who it's for</a>
        </nav>
        <div className="flex items-center gap-2">
          {user ? (
            <Link to="/app" className="rounded-full bg-strong px-5 py-2 text-sm font-medium text-on-accent hover:bg-cyan">Open dashboard</Link>
          ) : (
            <>
              <Link to="/login" className="rounded-full px-4 py-2 text-sm text-body hover:text-strong">Sign in</Link>
              <Link to="/register" className="rounded-full bg-strong px-5 py-2 text-sm font-medium text-on-accent hover:bg-cyan">Get started</Link>
            </>
          )}
        </div>
      </header>

      <section id="haldia" className="mx-auto max-w-6xl px-6 pb-16 pt-8">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-3xl text-center">
          <p className="inline-flex items-center gap-2 rounded-full border border-border-soft bg-white/80 px-3 py-1 text-xs font-medium text-cyan backdrop-blur">
            <Ship className="h-3.5 w-3.5" /> Smart India Hackathon 2026 · Coal chartering for India's East Coast
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.1] text-strong sm:text-6xl">
            <SplitText text="One tide. One lock." />
            <br />
            <SplitText text="Every fixture counts." delay={0.25} className="shiny-text" />
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-body">
            A coking-coal vessel bound for SAIL reaches Haldia only after lightering at Sagar, six hours up the Hooghly and through a tide-timed lock.
            This desk forecasts the freight market, checks what each port can physically take, and shows when a multi-voyage contract beats spot.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Magnet>
              <Link to={user ? "/app" : "/register"} className={btnPrimary}>
                {user ? "Open dashboard" : "Create an account"} <ArrowRight className="h-4 w-4" />
              </Link>
            </Magnet>
            {!user && (
              <Magnet>
                <Link to="/login" className="flex items-center rounded-full border border-border-soft bg-white/80 px-6 py-3 text-sm font-medium text-strong backdrop-blur transition hover:border-cyan/50">Sign in</Link>
              </Magnet>
            )}
          </div>
        </motion.div>

        <div className="relative mt-10 overflow-hidden rounded-3xl border border-border-soft bg-gradient-to-b from-sky-50 to-white shadow-[0_30px_80px_-30px_rgba(11,37,69,0.35)]">
          <Suspense fallback={<div className="flex h-[32rem] items-center justify-center text-sm text-muted">Loading Haldia…</div>}>
            <HaldiaScene className="h-[26rem] sm:h-[35rem]" onPhase={setPhase} />
          </Suspense>

          <div className="pointer-events-none absolute left-4 top-4 rounded-xl border border-border-soft bg-white/90 px-3 py-2 backdrop-blur">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-cyan">Haldia Dock Complex</p>
            <p className="text-xs text-body">Syama Prasad Mookerjee Port, Kolkata</p>
          </div>

          <div className="absolute inset-x-3 bottom-3 rounded-2xl border border-border-soft bg-white/92 p-3 shadow-lg backdrop-blur sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-[26rem]">
            <div className="flex gap-1.5">
              {HALDIA_PHASES.map((p) => (
                <div key={p.index} className={`h-1.5 flex-1 rounded-full transition-colors duration-500 ${p.index === phase ? "bg-cyan" : p.index < phase ? "bg-cyan/40" : "bg-border-soft"}`} />
              ))}
            </div>
            <p className="mt-2 text-[11px] font-semibold uppercase tracking-wider text-cyan">Step {phase + 1} of {HALDIA_PHASES.length}</p>
            <p className="text-sm font-semibold text-strong">{current.title}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-body">{current.text}</p>
          </div>
          <p className="pointer-events-none absolute bottom-2 right-4 hidden text-[10px] text-muted sm:block">Schematic, not to scale. Port dimensions from SMP Kolkata; ship motion is illustrative.</p>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { v: obs?.vessels ?? 0, s: "", l: "coal vessels seen at Haldia", d: obs ? `${obs.period_start} to ${obs.period_end}` : "" },
            { v: obs?.median_cargo_t ?? 0, s: " t", l: "median cargo per vessel", d: obs ? `range ${obs.min_cargo_t?.toLocaleString()}–${obs.max_cargo_t?.toLocaleString()} t` : "" },
            { v: obs?.median_draft_m ?? 0, s: " m", l: "median expected draft", d: obs ? `range ${obs.min_draft_m}–${obs.max_draft_m} m` : "", dec: 1 },
            { v: obs?.by_importer?.SAIL ?? 0, s: "", l: "of them bound for SAIL", d: "from port-trust daily reports" },
          ].map((c) => (
            <SpotlightCard key={c.l}>
              <div className="p-4">
                <p className="text-2xl font-bold text-strong"><AnimatedCounter value={c.v} suffix={c.s} decimals={c.dec ?? 0} /></p>
                <p className="mt-1 text-xs font-medium text-body">{c.l}</p>
                <p className="text-[11px] text-muted">{c.d}</p>
              </div>
            </SpotlightCard>
          ))}
        </div>
        <p className="mt-2 text-center text-[11px] text-muted">Real data: parsed from SMP Kolkata's public Haldia morning-position reports. Cargoes sit near 33,000 t because larger ships are lightened before the river.</p>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="grid items-stretch gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <h2 className="text-2xl font-bold text-strong">The market moves faster than a lock cycle</h2>
            <p className="mt-3 text-sm leading-relaxed text-body">
              Dry bulk freight can lose most of its value within two years: the Panamax index fell 86% between December 2013 and February 2016. Buying coal on single spot voyages means every fixture is priced
              on whatever the market is doing that day. Watch the real Baltic Panamax Index replay below.
            </p>
          </div>
          <div className="lg:col-span-3">
            <TiltCard>
              <SpotlightCard>
                <div className="p-5"><LiveChart indexName="BPI" label="Baltic Panamax Index (BPI)" height={230} compact /></div>
              </SpotlightCard>
            </TiltCard>
          </div>
        </div>
      </section>

      <section id="problem" className="mx-auto max-w-6xl px-6 pb-16">
        <h2 className="text-2xl font-bold text-strong">The problem, in numbers</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">From our research compendium, with sources cited in the full document.</p>
        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {PROBLEM_STATS.map((s) => (
            <SpotlightCard key={s.label} className="h-full">
              <div className="p-5">
                <p className="text-3xl font-bold text-strong"><AnimatedCounter value={s.value} prefix={s.prefix} suffix={s.suffix} decimals={s.decimals ?? 0} /></p>
                <p className="mt-2 text-sm text-body">{s.label}</p>
                <p className="mt-1 text-xs text-muted">{s.detail}</p>
              </div>
            </SpotlightCard>
          ))}
        </div>
      </section>

      <section id="capabilities" className="mx-auto max-w-6xl px-6 pb-16">
        <h2 className="text-2xl font-bold text-strong">What it does</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c, i) => (
            <motion.div key={c.title} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 4) * 0.06 }}>
              <TiltCard className="h-full">
                <SpotlightCard className="h-full">
                  <div className="p-5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan/10"><c.icon className="h-4.5 w-4.5 text-cyan" strokeWidth={1.75} /></div>
                    <h3 className="mt-3 text-sm font-semibold text-strong">{c.title}</h3>
                    <p className="mt-1.5 text-xs leading-relaxed text-body">{c.text}</p>
                  </div>
                </SpotlightCard>
              </TiltCard>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="flex gap-4 rounded-2xl border border-border-soft bg-white/80 p-5 backdrop-blur">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-strong text-sm font-semibold text-on-accent">{s.n}</span>
              <div>
                <h3 className="text-sm font-semibold text-strong">{s.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-body">{s.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y border-border-soft bg-white/60 py-5 backdrop-blur">
        <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-widest text-muted">Trained and checked against real sources</p>
        <Marquee items={SOURCES.map((s) => <span key={s} className="rounded-full border border-border-soft bg-white px-4 py-1.5 text-xs text-body">{s}</span>)} />
      </section>

      <section id="personas" className="mx-auto max-w-6xl px-6 pb-24 pt-16">
        <h2 className="text-2xl font-bold text-strong">Built for the people in the decision</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted">Pick a role when you sign up and the desk opens on the tools that role uses most.</p>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {personas.map((p) => {
            const v = personaView(p.key);
            return (
              <SpotlightCard key={p.key} glowColor={v.accent} className="h-full">
                <div className="p-5">
                  <v.icon className="h-5 w-5" style={{ color: `rgb(${v.accent})` }} strokeWidth={1.75} />
                  <h3 className="mt-3 text-sm font-semibold text-strong">{p.label}</h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-body">{p.description}</p>
                </div>
              </SpotlightCard>
            );
          })}
        </div>
        <div className="mt-10 flex justify-center">
          <Magnet>
            <Link to={user ? "/app" : "/register"} className={btnPrimary}>
              <Gauge className="h-4 w-4" /> {user ? "Open dashboard" : "Start with your role"}
            </Link>
          </Magnet>
        </div>
      </section>

      <footer className="border-t border-border-soft bg-white/70">
        <div className="mx-auto max-w-6xl px-6 py-8 text-xs leading-relaxed text-muted">
          <p>
            Prices shown are real ingested data, replayed rather than streamed live. The Baltic freight indices end in July 2019 (the live feed is a paid subscription); coal, currency and equity series run to 2024–2026. Cost figures in the tools are labelled illustrative estimates, not live quotes.
            The Haldia scene is a schematic built from public port-trust figures.
          </p>
          <p className="mt-3">Built for the Smart India Hackathon 2026.</p>
        </div>
      </footer>
    </div>
  );
}
