import { useState } from "react";
import { motion } from "framer-motion";
import { Calculator, TrendingUp, TrendingDown, Anchor, PiggyBank } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { simulateCoaVsSpot, estimateRoi, type CoaVsSpotResult, type RoiResult } from "../lib/api";

const INDICES = ["BCI", "BPI", "BSI", "BHSI"];

function CoaVsSpotTool() {
  const [indexName, setIndexName] = useState("BPI");
  const [rate, setRate] = useState("15");
  const [tonnesPerFixture, setTonnesPerFixture] = useState("75000");
  const [numFixtures, setNumFixtures] = useState("6");
  const [intervalDays, setIntervalDays] = useState("30");
  const [result, setResult] = useState<CoaVsSpotResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await simulateCoaVsSpot({
        index_name: indexName,
        current_rate_usd_per_tonne: Number(rate),
        cargo_tonnes_per_fixture: Number(tonnesPerFixture),
        num_fixtures: Number(numFixtures),
        interval_days: Number(intervalDays),
      });
      setResult(r);
    } catch {
      setError("Simulation failed — check inputs or backend status.");
    } finally {
      setLoading(false);
    }
  }

  const coaWins = result && result.recommendation === "Lock in COA";

  return (
    <SpotlightCard>
      <div className="p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
          <Calculator className="h-4 w-4 text-cyan" /> COA-vs-Spot Simulator
        </h2>
        <p className="mt-1 text-xs text-muted">
          Directly answers the problem statement's objective: should we lock in a Contract of Affreightment, or
          keep fixing spot voyage-by-voyage?
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <label className="text-xs text-muted">
            Index
            <select className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={indexName} onChange={(e) => setIndexName(e.target.value)}>
              {INDICES.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </label>
          <label className="text-xs text-muted">
            Current $/t
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={rate} onChange={(e) => setRate(e.target.value)} />
          </label>
          <label className="text-xs text-muted">
            Tonnes/fixture
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={tonnesPerFixture} onChange={(e) => setTonnesPerFixture(e.target.value)} />
          </label>
          <label className="text-xs text-muted">
            # Fixtures
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={numFixtures} onChange={(e) => setNumFixtures(e.target.value)} />
          </label>
          <label className="text-xs text-muted">
            Days apart
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={intervalDays} onChange={(e) => setIntervalDays(e.target.value)} />
          </label>
        </div>

        <button onClick={run} disabled={loading} className="mt-4 rounded-md bg-cyan/90 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50">
          {loading ? "Simulating…" : "Run simulation"}
        </button>

        {error && <p className="mt-3 text-sm text-down">{error}</p>}

        {result && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
            <div className={`flex items-center justify-between rounded-lg border p-4 ${coaWins ? "border-up/30 bg-up/10" : "border-amber/30 bg-amber/10"}`}>
              <span className={`text-sm font-semibold ${coaWins ? "text-up" : "text-amber"}`}>{result.recommendation}</span>
              <span className={`flex items-center gap-1 text-lg font-bold ${result.expected_savings_usd >= 0 ? "text-up" : "text-down"}`}>
                {result.expected_savings_usd >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                ${Math.abs(result.expected_savings_usd).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </div>
            <p className="mt-3 text-xs text-muted">{result.rationale}</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-md border border-border-soft bg-panel-light/50 p-2">
                <p className="text-muted">COA total</p>
                <p className="font-semibold text-strong">${result.total_coa_cost_usd.toLocaleString()}</p>
              </div>
              <div className="rounded-md border border-border-soft bg-panel-light/50 p-2">
                <p className="text-muted">Spot total (forecast)</p>
                <p className="font-semibold text-strong">${result.total_spot_cost_usd.toLocaleString()}</p>
              </div>
              <div className="rounded-md border border-border-soft bg-panel-light/50 p-2">
                <p className="text-muted">Spot volatility (±)</p>
                <p className="font-semibold text-strong">${result.spot_cost_std_usd.toLocaleString()}</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </SpotlightCard>
  );
}

function RoiTool() {
  const [indexName, setIndexName] = useState("BPI");
  const [annualTonnes, setAnnualTonnes] = useState("15000000");
  const [assumedRate, setAssumedRate] = useState("12");
  const [capturedPct, setCapturedPct] = useState("20");
  const [result, setResult] = useState<RoiResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      const r = await estimateRoi({
        index_name: indexName,
        annual_cargo_tonnes: Number(annualTonnes),
        assumed_freight_usd_per_tonne: Number(assumedRate),
        captured_pct: Number(capturedPct),
      });
      setResult(r);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SpotlightCard glowColor="52,211,153">
      <div className="p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-strong">
          <PiggyBank className="h-4 w-4 text-up" /> ROI Calculator
        </h2>
        <p className="mt-1 text-xs text-muted">
          Estimates annual savings potential from better-timed chartering, using the freight index's own real
          historical volatility as the opportunity size.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label className="text-xs text-muted">
            Index
            <select className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={indexName} onChange={(e) => setIndexName(e.target.value)}>
              {INDICES.map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </label>
          <label className="text-xs text-muted">
            Annual tonnes
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={annualTonnes} onChange={(e) => setAnnualTonnes(e.target.value)} />
          </label>
          <label className="text-xs text-muted">
            Assumed $/t
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={assumedRate} onChange={(e) => setAssumedRate(e.target.value)} />
          </label>
          <label className="text-xs text-muted">
            Captured %
            <input className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-2 py-1.5 text-sm text-strong" value={capturedPct} onChange={(e) => setCapturedPct(e.target.value)} />
          </label>
        </div>

        <button onClick={run} disabled={loading} className="mt-4 rounded-md bg-up/90 px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-up disabled:opacity-50">
          {loading ? "Calculating…" : "Estimate savings"}
        </button>

        {result && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
            <p className="text-3xl font-bold text-up">${result.estimated_annual_savings_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}<span className="text-sm text-muted">/year</span></p>
            <p className="mt-2 text-xs text-muted">{result.notes}</p>
          </motion.div>
        )}
      </div>
    </SpotlightCard>
  );
}

export default function Financial() {
  return (
    <div className="space-y-6">
      <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold text-strong">
        Financial Tools
      </motion.h1>
      <p className="text-xs text-muted flex items-center gap-1.5">
        <Anchor className="h-3.5 w-3.5" /> All figures are illustrative estimates from real ingested data and researched benchmarks, not live quotes.
      </p>
      <CoaVsSpotTool />
      <RoiTool />
    </div>
  );
}
