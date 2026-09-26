import { useCallback, useEffect, useState } from "react";
import { ArrowLeftRight, RefreshCw } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import { api } from "../lib/api";

interface Rate {
  live: boolean; rate: number | null; rate_date: string | null; source: string | null; note?: string; fetched_at: string;
  model_rate: { rate: number; date: string; source: string } | null; difference_vs_model_pct?: number; history: { date: string; inr_per_usd: number }[];
}

const nice = (n: number, d = 2) => n.toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });

/** Slim bar at the bottom of every page: today's USD to INR rate with its date and source, and a two-way converter. */
export default function FxBar() {
  const [r, setR] = useState<Rate | null>(null);
  const [err, setErr] = useState(false);
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("1000000");
  const [dir, setDir] = useState<"USD" | "INR">("USD");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try { setR((await api.get<Rate>("/fx/rate")).data); setErr(false); } catch { setErr(true); } finally { setBusy(false); }
  }, []);
  useEffect(() => { void load(); const id = setInterval(() => void load(), 15 * 60_000); return () => clearInterval(id); }, [load]);

  const n = Number(amount.replace(/,/g, ""));
  const ok = r?.rate && Number.isFinite(n) && n >= 0;
  const result = ok ? (dir === "USD" ? n * r!.rate! : n / r!.rate!) : null;
  const crore = dir === "USD" && result !== null ? result / 1e7 : null;

  return (
    <footer className="sticky bottom-0 z-30 border-t border-border-soft bg-white/95 text-xs backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 sm:px-6 lg:px-8">
        <span className="font-semibold text-strong">USD / INR</span>
        {r?.rate ? (
          <>
            <span className="text-base font-semibold tabular-nums text-strong">₹{nice(r.rate)}</span>
            <span className={r.live ? "text-up" : "text-warn"}>{r.live ? "● live" : "● stored (live source unreachable)"}</span>
            <span className="text-muted">as of {r.rate_date} · {r.source}</span>
            {r.history.length > 1 && (
              <span className="hidden h-6 w-24 sm:inline-block" aria-label="30-day trend">
                <ResponsiveContainer width="100%" height="100%"><LineChart data={r.history}><YAxis hide domain={["dataMin", "dataMax"]} /><Line type="monotone" dataKey="inr_per_usd" stroke="#0e7490" strokeWidth={1.5} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer>
              </span>
            )}
          </>
        ) : <span className="text-muted">{err ? "Rate unavailable right now" : "Loading rate…"}</span>}
        <button onClick={() => setOpen((o) => !o)} className="ml-auto inline-flex items-center gap-1 rounded-md border border-border-soft px-2 py-1 text-strong hover:bg-panel-light">
          <ArrowLeftRight className="h-3.5 w-3.5" /> Converter
        </button>
        <button onClick={() => void load()} aria-label="Refresh rate" className="rounded-md p-1 text-muted hover:text-strong"><RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} /></button>
      </div>
      {open && (
        <div className="border-t border-border-soft px-4 pb-3 pt-2 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-muted">Amount
              <input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" className="mt-1 block w-44 rounded-lg border border-border-soft bg-white px-2.5 py-1.5 text-sm text-strong outline-none focus:border-cyan" />
            </label>
            <div className="inline-flex overflow-hidden rounded-lg border border-border-soft">
              {(["USD", "INR"] as const).map((c) => (
                <button key={c} onClick={() => setDir(c)} className={`px-3 py-1.5 text-sm ${dir === c ? "bg-strong text-on-accent" : "bg-white text-strong hover:bg-panel-light"}`}>{c} to {c === "USD" ? "INR" : "USD"}</button>
              ))}
            </div>
            <div className="text-sm text-strong">
              {result !== null ? (<>
                <span className="text-base font-semibold tabular-nums">{dir === "USD" ? "₹" : "$"}{nice(result, dir === "USD" ? 2 : 2)}</span>
                {crore !== null && crore >= 0.01 && <span className="ml-2 text-muted">= ₹{nice(crore, 3)} crore</span>}
              </>) : <span className="text-muted">Enter an amount</span>}
            </div>
          </div>
          <p className="mt-2 text-[11px] text-muted">
            {r?.note ?? ""} {r?.model_rate && <>The cost estimates in this app convert with the stored Federal Reserve rate, ₹{nice(r.model_rate.rate)} ({r.model_rate.date}){r.difference_vs_model_pct !== undefined && <>; today's rate is {r.difference_vs_model_pct >= 0 ? "+" : ""}{r.difference_vs_model_pct}% different</>}, so every rupee figure stays reproducible.</>}
          </p>
        </div>
      )}
    </footer>
  );
}
