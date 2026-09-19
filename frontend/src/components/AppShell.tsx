import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Anchor, Menu, X } from "lucide-react";
import NoAccess from "./NoAccess";
import CommandPalette from "./CommandPalette";
import { routeAllowed } from "../lib/personas";
import Sidebar from "./Sidebar";
import TickerTape from "./TickerTape";
import OceanBackdrop from "./OceanBackdrop";
import { useAuth } from "../lib/auth";
import { useUiScale } from "../lib/scale";

/** Everything under /app requires a signed-in user. Below 1024 px the sidebar becomes a slide-in drawer. */
export default function AppShell() {
  const { user, loading, can } = useAuth();
  const { pathname } = useLocation();
  const scale = useUiScale();
  const [drawer, setDrawer] = useState(false);

  useEffect(() => { setDrawer(false); }, [pathname]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted">Loading…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex min-h-screen text-strong">
      <OceanBackdrop />
      <CommandPalette />
      <div className="hidden lg:block"><Sidebar /></div>

      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-strong/40 backdrop-blur-sm" onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 left-0 shadow-2xl"><Sidebar /></div>
          <button onClick={() => setDrawer(false)} aria-label="Close menu" className="absolute right-4 top-4 rounded-full bg-white p-2 text-strong shadow"><X className="h-5 w-5" /></button>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-border-soft bg-white/80 px-4 py-2 backdrop-blur lg:hidden">
          <button onClick={() => setDrawer(true)} aria-label="Open menu" className="rounded-lg p-1.5 text-strong hover:bg-panel-light"><Menu className="h-5 w-5" /></button>
          <Anchor className="h-4 w-4 text-cyan" />
          <span className="text-sm font-semibold text-strong">East Coast Freight Desk</span>
        </div>
        {can("market:read") && <TickerTape />}
        <main className="flex-1 overflow-x-hidden p-4 sm:p-6 lg:p-8" key={scale}>
          {routeAllowed(pathname.replace(/\/$/, ""), can) ? <Outlet /> : <NoAccess />}
        </main>
      </div>
    </div>
  );
}
