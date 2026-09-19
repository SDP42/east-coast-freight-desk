import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Anchor, ArrowRight, Brain, Briefcase, Calculator, Compass, Dices, Flame, Globe2, Landmark, LineChart, LogIn, MapPinned, MessageSquareText, Mountain, ShieldAlert, ShieldCheck,
  Ship, Timer, UserRound, Zap,
} from "lucide-react";
import OceanBackdrop from "../components/OceanBackdrop";
import TickerTape from "../components/TickerTape";
import LiveChart from "../components/LiveChart";
import SpotlightCard from "../components/SpotlightCard";
import Magnet from "../components/Magnet";
import Marquee from "../components/Marquee";
import MapExplorer from "../components/MapExplorer";
import ParticleTextRaw from "../components/rb/ParticleText";
import BorderGlowRaw from "../components/rb/BorderGlow";
import CarouselRaw from "../components/rb/Carousel";
import { Ripple } from "../components/rb/Ripple";
import Aurora from "../components/rb/Aurora";
import ShinyText from "../components/rb/ShinyText";
import BlurText from "../components/rb/BlurText";
import GradientText from "../components/rb/GradientText";
import CountUp from "../components/rb/CountUp";
import { useAuth } from "../lib/auth";

const ParticleText = ParticleTextRaw as unknown as React.ComponentType<Record<string, unknown>>;
const BorderGlow = BorderGlowRaw as unknown as React.ComponentType<Record<string, unknown> & { children?: React.ReactNode }>;
const Carousel = CarouselRaw as unknown as React.ComponentType<Record<string, unknown>>;

const GLOW = { backgroundColor: "#ffffff", glowColor: "190 85 38", colors: ["#0e7490", "#7c3aed", "#d97706"], borderRadius: 22, glowRadius: 26, fillOpacity: 0.28, edgeSensitivity: 26 };

const CAPABILITIES = [
  { icon: Timer, title: "Urgent Fixture Desk", text: "A plant is about to run short. Get the fastest safe ship, the on-time probability and a walk-away price in seconds.", to: "/app/urgent" },
  { icon: Flame, title: "What-If Studio", text: "Move freight, rupee, fuel, delays and Red Sea reroutes and watch landed cost and trip time change live.", to: "/app/whatif" },
  { icon: MessageSquareText, title: "Ask by voice or chat", text: "Type or speak a question; a local model routes it to the engines, and only answers what your role may see.", to: "/app/ask" },
  { icon: LineChart, title: "Forecasts with proof", text: "ARIMA, XGBoost and deep models compared honestly on the same forecasts, with backtests and significance tests.", to: "/app/lab" },
  { icon: MapPinned, title: "Berth-fit engine", text: "Draft, length, beam and tidal windows for seven ports, with part-laden calls handled per port.", to: "/app/ports" },
  { icon: Compass, title: "Five origins, one cargo", text: "Australia, the US, Mozambique, Russia and Indonesia ranked on cost, time and risk, Pareto-optimal ones marked.", to: "/app/recommendation" },
  { icon: ShieldAlert, title: "Route risk", text: "Disruptions, congestion and volatility combined into one explained score per route.", to: "/app/risk" },
  { icon: Calculator, title: "COA vs spot", text: "Simulate locking a contract against staying spot, with the savings case for finance.", to: "/app/financial" },
];

const ROLES = [
  { id: 1, title: "Administrator", description: "Everything, plus users, roles, port assignments and the audit log.", icon: <ShieldCheck className="carousel-icon" /> },
  { id: 2, title: "Finance & Treasury", description: "All commercial data, hedging, demand and every fixture. No user management.", icon: <Landmark className="carousel-icon" /> },
  { id: 3, title: "Procurement Manager", description: "Sourcing, freight, cost and every fixture. Decides when and how to buy.", icon: <Briefcase className="carousel-icon" /> },
  { id: 4, title: "Chartering Analyst", description: "Markets, forecasts and recommendations. Sees only their own fixtures.", icon: <LineChart className="carousel-icon" /> },
  { id: 5, title: "Port & Logistics Officer", description: "Only the ports assigned to them: berth fit, congestion, cyclone risk and laytime claims.", icon: <Anchor className="carousel-icon" /> },
  { id: 6, title: "Viewer", description: "Public market data. New accounts start here until an administrator assigns a role.", icon: <UserRound className="carousel-icon" /> },
];

const SOURCES = ["USDA ocean freight rates", "US BLS producer price indices", "US EIA Brent crude", "Federal Reserve exchange rates", "NOAA IBTrACS", "Ministry of Ports", "SAIL annual reports", "CAG audit 2025", "Natural Earth", "Public domain only"];
const SCENES = [
  { icon: Globe2, title: "Trade globe", text: "Sea lanes and chokepoints in 3D.", to: "/app/globe", tint: "from-sky-100 to-cyan-50" },
  { icon: Dices, title: "Forecast fan", text: "400 possible futures, drawn in depth.", to: "/app/risklab", tint: "from-violet-100 to-fuchsia-50" },
  { icon: Mountain, title: "Market terrain", text: "Eight series as one landscape.", to: "/app/terrain", tint: "from-amber-100 to-orange-50" },
  { icon: Brain, title: "Model lab", text: "Deep learning against classical models.", to: "/app/lab", tint: "from-emerald-100 to-teal-50" },
];

export default function Landing() {
  const { user } = useAuth();
  const primary = "flex items-center gap-2 rounded-full bg-strong px-7 py-3.5 text-sm font-semibold text-on-accent shadow-xl shadow-slate-900/15 transition hover:bg-cyan";
  const stats = [
    { v: 87, s: "%", l: "of SAIL's clean coking coal is imported", d: "16.92 of 19.37 MT, FY24 annual report" },
    { v: 94, s: "%", l: "of imported coal on long-term agreements", d: "CAG audit, FY17 to FY23" },
    { v: 374, s: "", l: "demurrage cases in four years", d: "CAG audit of SAIL" },
    { v: 69, s: " h", l: "average turnaround at Visakhapatnam", d: "vs 45 h at Paradip, FY25 Ministry of Ports" },
  ];


  return (
    <div className="min-h-screen overflow-x-clip text-body">
      <OceanBackdrop />
      <TickerTape />

      <header className="sticky top-0 z-40 border-b border-border-soft/70 bg-white/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-strong"><Anchor className="h-5 w-5 text-white" strokeWidth={1.75} /></div>
            <span className="text-sm font-semibold text-strong">East Coast Freight Desk</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-muted md:flex">
            <a href="#map" className="hover:text-strong">Map</a>
            <a href="#decide" className="hover:text-strong">Decide fast</a>
            <a href="#capabilities" className="hover:text-strong">Capabilities</a>
            <a href="#roles" className="hover:text-strong">Roles</a>
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <Link to="/app" className="rounded-full bg-strong px-5 py-2 text-sm font-medium text-on-accent hover:bg-cyan">Open dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="hidden rounded-full px-4 py-2 text-sm text-body hover:text-strong sm:block">Sign in</Link>
                <Link to="/login" className="flex items-center gap-1.5 rounded-full bg-strong px-5 py-2 text-sm font-medium text-on-accent hover:bg-cyan"><LogIn className="h-3.5 w-3.5" /> Try the demo</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative mx-auto max-w-6xl px-6 pb-6 pt-10 text-center">
        <div className="pointer-events-none absolute inset-x-0 -top-16 h-[36rem] opacity-80 [mask-image:linear-gradient(to_bottom,black_30%,transparent)]" aria-hidden>
          <Aurora colorStops={["#67e8f9", "#c4b5fd", "#fcd34d"]} amplitude={0.9} blend={0.65} speed={0.6} lightMode />
        </div>
        <Ripple baseSize={260} circles={5} className="[mask-image:radial-gradient(ellipse_at_50%_35%,black,transparent_70%)]" />
        <motion.p initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="relative mx-auto inline-flex items-center gap-2 rounded-full border border-border-soft bg-white/80 px-3.5 py-1.5 text-xs font-medium text-cyan shadow-sm backdrop-blur">
          <Ship className="h-3.5 w-3.5" /> <ShinyText text="Smart India Hackathon 2026 · Coal chartering for India's East Coast" color="#0e7490" shineColor="#38bdf8" speed={3} />
        </motion.p>
        <div className="relative mx-auto mt-2 h-[13rem] max-w-4xl sm:h-[16rem]">
          <ParticleText
            text="One tide. One lock." particleSize={3} density={4} color="#0b2545" highlightColor="#0e9fbf" scatter={230} gatherDuration={1700} stagger={520}
            pointerRepel={46} repelRadius={130} idleDrift={0.8} trigger="hover" fontSize="clamp(2.6rem, 8.4vw, 6.4rem)" fontWeight={800} glow={false}
          />
        </div>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="relative -mt-4"><GradientText colors={["#0e7490", "#7c3aed", "#d97706", "#0e7490"]} animationSpeed={6} className="text-2xl font-bold sm:text-4xl">Every fixture counts.</GradientText></motion.div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }} className="relative mx-auto mt-5 max-w-2xl text-base leading-relaxed text-body">
          A coking-coal ship bound for SAIL is lightened at Sagar, sails six hours up the Hooghly and passes a tide-timed lock. This desk forecasts the market, checks what each port can take,
          and answers the last-minute call: <b className="text-strong">what if freight jumps, the port stalls, or we need coal in two weeks?</b>
        </motion.p>
        <div className="relative mt-8 flex flex-wrap items-center justify-center gap-3">
          <Magnet><Link to={user ? "/app" : "/login"} className={primary}>{user ? "Open dashboard" : "Try the live demo"} <ArrowRight className="h-4 w-4" /></Link></Magnet>
          {!user && <Magnet><Link to="/register" className="flex items-center rounded-full border border-border-soft bg-white/85 px-7 py-3.5 text-sm font-medium text-strong backdrop-blur transition hover:border-cyan">Create an account</Link></Magnet>}
        </div>
        <div className="relative mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted">
          {["6 roles with real access control", "Voice assistant", "4 interactive 3D views", "Deep learning, honestly compared"].map((t) => <span key={t} className="flex items-center gap-1.5"><Zap className="h-3 w-3 text-amber" />{t}</span>)}
        </div>
      </section>

      {/* Where the coal comes from: globe, flat map, regions and ports */}
      <section id="map" className="mx-auto max-w-6xl px-6 pb-14 pt-6">
        <div className="mb-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-cyan">Where the coal comes from</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-strong">Five origins, seven ports, one desk.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-body">More than half of India's coking coal comes from Australia; Mozambique, the US and Russia fill the rest, and the mix is shifting. Every lane has its own distance, weather and canal risk, and each end has its own draft limit. Switch views to explore.</p>
        </div>
        <MapExplorer />

        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {stats.map((c) => (
            <BorderGlow key={c.l} {...GLOW}>
              <div className="p-5">
                <p className="text-3xl font-bold text-strong"><CountUp to={c.v} duration={1.6} separator="," />{c.s}</p>
                <p className="mt-1 text-sm font-medium text-body">{c.l}</p>
                <p className="text-[11px] text-muted">{c.d}</p>
              </div>
            </BorderGlow>
          ))}
        </div>
        <p className="mt-2 text-center text-[11px] text-muted">Figures from SAIL's annual report, the CAG audit and the Ministry of Ports (sources in the README). Haldia takes about 35,000 t per vessel because larger ships are lightened at Sagar first.</p>
      </section>

      {/* Decide fast */}
      <section id="decide" className="mx-auto max-w-6xl px-6 pb-16">
        <p className="text-xs font-semibold uppercase tracking-widest text-cyan">When the call comes in at 6 pm</p>
        <BlurText text="Built for the urgent decision, not just the quarterly report." delay={70} animateBy="words" direction="top" className="mt-2 max-w-2xl text-3xl font-bold text-strong" />
        <div className="mt-8 grid gap-5 lg:grid-cols-2">
          <BorderGlow {...GLOW} glowColor="24 90 45" colors={["#d97706", "#dc2626", "#7c3aed"]}>
            <div className="grid gap-5 p-6 sm:grid-cols-5">
              <div className="sm:col-span-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber/10"><Timer className="h-5 w-5 text-amber" /></div>
                <h3 className="mt-3 text-xl font-bold text-strong">Urgent Fixture Desk</h3>
                <p className="mt-2 text-sm leading-relaxed text-body">Tell it the port, the tonnes and the deadline. It costs every origin, vessel and speed, simulates 2,000 arrivals, and tells you the fastest safe option, the chance of being on time, and the most you should pay.</p>
                <Link to={user ? "/app/urgent" : "/login"} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-amber hover:underline">See it work <ArrowRight className="h-4 w-4" /></Link>
              </div>
              <div className="flex flex-col justify-center gap-2 sm:col-span-2">
                {[["Panamax · Mozambique", 78, "100%"], ["Supramax · Australia", 92, "96%"], ["Capesize · US", 118, "41%"]].map(([n, w, p]) => (
                  <div key={String(n)}><div className="flex justify-between text-[10px] text-muted"><span>{n}</span><span>{p} on time</span></div>
                    <div className="mt-0.5 h-2 rounded-full bg-panel-light"><motion.div initial={{ width: 0 }} whileInView={{ width: `${Math.min(100, Number(w))}%` }} viewport={{ once: true }} transition={{ duration: 1 }} className={`h-2 rounded-full ${Number(w) > 100 ? "bg-down" : "bg-cyan"}`} /></div></div>
                ))}
                <p className="text-[10px] text-muted">Illustration of the desk's timeline bars</p>
              </div>
            </div>
          </BorderGlow>
          <BorderGlow {...GLOW} glowColor="268 70 55" colors={["#7c3aed", "#0e7490", "#d97706"]}>
            <div className="grid gap-5 p-6 sm:grid-cols-5">
              <div className="sm:col-span-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100"><Flame className="h-5 w-5 text-violet-700" /></div>
                <h3 className="mt-3 text-xl font-bold text-strong">What-If Studio</h3>
                <p className="mt-2 text-sm leading-relaxed text-body">Drag freight, rupee, fuel, delays or a Red Sea reroute and see landed cost, trip time and a tornado of what matters most. One-click crisis playbooks; save and compare scenarios.</p>
                <Link to={user ? "/app/whatif" : "/login"} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-violet-700 hover:underline">Try a scenario <ArrowRight className="h-4 w-4" /></Link>
              </div>
              <div className="flex flex-col justify-center gap-1.5 sm:col-span-2">
                {[["Reroute", 96], ["Freight", 64], ["Speed", 30], ["Fuel", 27], ["Rupee", 24]].map(([n, w]) => (
                  <div key={String(n)} className="flex items-center gap-2 text-[10px] text-muted"><span className="w-10">{n}</span>
                    <motion.div initial={{ width: 0 }} whileInView={{ width: `${w}%` }} viewport={{ once: true }} transition={{ duration: 0.9 }} className="h-2 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-400" /></div>
                ))}
                <p className="text-[10px] text-muted">Illustration of a tornado chart</p>
              </div>
            </div>
          </BorderGlow>
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="mx-auto max-w-6xl px-6 pb-16">
        <h2 className="text-3xl font-bold text-strong">Everything in one desk</h2>
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((c, i) => (
            <motion.div key={c.title} initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 4) * 0.06 }}>
              <Link to={user ? c.to : "/login"} className="block h-full">
                <BorderGlow {...GLOW}>
                  <div className="p-5">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan/10"><c.icon className="h-5 w-5 text-cyan" strokeWidth={1.75} /></div>
                    <h3 className="mt-3 text-sm font-bold text-strong">{c.title}</h3>
                    <p className="mt-1.5 text-xs leading-relaxed text-body">{c.text}</p>
                  </div>
                </BorderGlow>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* 3D and market */}
      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="grid items-stretch gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <h2 className="text-3xl font-bold text-strong">See risk, don't just read it</h2>
            <p className="mt-3 text-sm leading-relaxed text-body">Four interactive 3D views, written in plain three.js: the globe of sea lanes and chokepoints, a fan of possible futures, and a terrain of the markets. Below, the real Panamax index replays with spikes and collapses flagged.</p>
            <div className="mt-5 grid grid-cols-2 gap-3">
              {SCENES.map((s) => (
                <Link key={s.title} to={user ? s.to : "/login"} className={`group rounded-2xl border border-border-soft bg-gradient-to-br ${s.tint} p-4 transition hover:-translate-y-0.5 hover:shadow-md`}>
                  <s.icon className="h-5 w-5 text-strong" strokeWidth={1.75} />
                  <p className="mt-2 text-sm font-semibold text-strong">{s.title}</p>
                  <p className="text-[11px] leading-snug text-body">{s.text}</p>
                </Link>
              ))}
            </div>
          </div>
          <div className="lg:col-span-3">
            <SpotlightCard className="h-full"><div className="p-5"><LiveChart indexName="OCEAN_GULF_JAPAN" label="USDA grain ocean rate, Gulf to Japan (US$/t)" height={300} compact /></div></SpotlightCard>
          </div>
        </div>
      </section>

      {/* Roles */}
      <section id="roles" className="mx-auto max-w-6xl px-6 pb-20">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <div>
            <h2 className="text-3xl font-bold text-strong">The same question, a different answer for each person</h2>
            <p className="mt-3 text-sm leading-relaxed text-body">Access is a role an administrator assigns and it is enforced in the API and the database queries. Ask "How much coking coal does SAIL import?" as a port officer and the desk refuses and logs it; ask as Finance and it answers. Drag the cards to meet the six roles.</p>
            <Link to={user ? "/app/access" : "/login"} className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-cyan hover:underline">Sign in with a demo role <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <div className="flex justify-center"><Carousel items={ROLES} baseWidth={360} autoplay autoplayDelay={3200} pauseOnHover loop /></div>
        </div>
      </section>

      <section className="border-y border-border-soft bg-white/60 py-5 backdrop-blur">
        <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-widest text-muted">Real, open data</p>
        <Marquee items={SOURCES.map((s) => <span key={s} className="rounded-full border border-border-soft bg-white px-4 py-1.5 text-xs text-body">{s}</span>)} />
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h2 className="text-3xl font-bold text-strong">Meet the desk</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-body">Six demo accounts, one per role, sign in with one click and hold sample data only.</p>
        <div className="mt-6 flex justify-center"><Magnet><Link to={user ? "/app" : "/login"} className={primary}><LogIn className="h-4 w-4" /> {user ? "Open dashboard" : "Choose a demo role"}</Link></Magnet></div>
      </section>

      <footer className="border-t border-border-soft bg-white/70">
        <div className="mx-auto max-w-6xl px-6 py-8 text-xs leading-relaxed text-muted">
          <p>
            Prices shown are real ingested data, replayed rather than streamed live. Every series is public-domain US-government or Federal Reserve data, current to 2026, fetched free with no accounts or keys.
            Cost figures are illustrative estimates, not quotes. The Haldia scene is a schematic built from public port-trust figures. Minute ticks on the Live Desk are simulated.
          </p>
          <p className="mt-3">Built for the Smart India Hackathon 2026.</p>
        </div>
      </footer>
    </div>
  );
}
