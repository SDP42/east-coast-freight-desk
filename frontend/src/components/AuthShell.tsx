import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Anchor, ShieldCheck, Ship } from "lucide-react";
import OceanBackdrop from "./OceanBackdrop";
import LiveChart from "./LiveChart";
import SpotlightCard from "./SpotlightCard";

/** Shared two-panel layout for sign-in and register: form on the left, a live market card on the right. */
export default function AuthShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,0.85fr)]">
      <OceanBackdrop />
      <div className="flex flex-col p-6 sm:p-10">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-strong"><Anchor className="h-5 w-5 text-white" strokeWidth={1.75} /></div>
          <span className="text-sm font-semibold text-strong">East Coast Freight Desk</span>
        </Link>
        <div className="flex flex-1 items-center justify-center py-8">
          <div className={`w-full ${wide ? "max-w-2xl" : "max-w-sm"}`}>{children}</div>
        </div>
        <p className="text-xs text-muted">Smart India Hackathon 2026 · accounts are stored in this deployment's own database.</p>
      </div>

      <div className="hidden flex-col justify-center gap-6 border-l border-border-soft bg-white/50 p-10 backdrop-blur lg:flex">
        <div>
          <h2 className="text-3xl font-bold leading-tight text-strong">The market moves every day. Your decisions should move first.</h2>
          <p className="mt-3 max-w-md text-sm text-body">Forecasts, berth fit and cost comparison for India's East Coast coal imports.</p>
        </div>
        <SpotlightCard className="max-w-md"><div className="p-4"><LiveChart indexName="BDI" label="Baltic Dry Index" height={150} compact /></div></SpotlightCard>
        <ul className="max-w-md space-y-3 text-sm text-body">
          <li className="flex gap-3"><Ship className="mt-0.5 h-4 w-4 shrink-0 text-cyan" /> Checked against real coal vessels discharging at Haldia.</li>
          <li className="flex gap-3"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-cyan" /> Passwords are hashed with bcrypt; repeated wrong attempts lock sign-in for ten minutes.</li>
        </ul>
      </div>
    </div>
  );
}
