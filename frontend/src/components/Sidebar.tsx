import { NavLink } from "react-router-dom";
import {
  Anchor, LayoutDashboard, TrendingUp, Compass, MapPinned, ShieldAlert, Calculator, FlaskConical, Activity, LogOut, Map, MessageSquareText, UserCircle,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { PERSONA_LABEL, personaView } from "../lib/personas";

const links = [
  { to: "/app", key: "overview", label: "Overview", icon: LayoutDashboard },
  { to: "/app/ask", key: "ask", label: "Ask the Desk", icon: MessageSquareText },
  { to: "/app/markets", key: "markets", label: "Markets", icon: Activity },
  { to: "/app/forecast", key: "forecast", label: "Freight Forecast", icon: TrendingUp },
  { to: "/app/recommendation", key: "recommendation", label: "Chartering Recommendation", icon: Compass },
  { to: "/app/ports", key: "ports", label: "Port Compatibility", icon: MapPinned },
  { to: "/app/map", key: "map", label: "Port Map", icon: Map },
  { to: "/app/risk", key: "risk", label: "Risk & Disruptions", icon: ShieldAlert },
  { to: "/app/financial", key: "financial", label: "Financial Tools", icon: Calculator },
  { to: "/app/scenario", key: "scenario", label: "Scenario Sandbox", icon: FlaskConical },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const view = personaView(user?.role);
  const focus = new Set(
    { procurement_manager: ["ask", "recommendation", "financial"], chartering_analyst: ["markets", "forecast", "recommendation"],
      port_ops: ["ports", "risk", "map"], finance_head: ["financial", "markets", "scenario"] }[user?.role ?? ""] ?? [],
  );
  const displayName = user?.full_name || user?.email || "";

  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col gap-6 border-r border-border-soft bg-ink/80 p-5 backdrop-blur-xl">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-cyan/20 bg-gradient-to-br from-cyan/20 to-steel/40">
          <Anchor className="h-5 w-5 text-cyan" strokeWidth={1.75} />
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-widest text-cyan/70">SIH 2026</p>
          <h1 className="text-sm font-semibold leading-snug text-strong">East Coast Freight Desk</h1>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {links.map(({ to, key, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/app"}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                isActive ? "bg-panel-light text-strong shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]" : "text-muted hover:bg-panel hover:text-strong"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`h-4 w-4 ${isActive ? "text-cyan" : "text-muted group-hover:text-cyan"}`} strokeWidth={1.75} />
                <span className="flex-1">{label}</span>
                {focus.has(key) && <span title={`Suggested for ${PERSONA_LABEL[user?.role ?? ""] ?? "you"}`} className="h-1.5 w-1.5 rounded-full bg-cyan" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto space-y-3">
        <div className="rounded-lg border border-border-soft bg-panel p-3">
          <div className="flex items-center gap-2">
            <view.icon className="h-4 w-4 shrink-0" style={{ color: `rgb(${view.accent})` }} strokeWidth={1.75} />
            <p className="truncate text-xs font-medium text-strong">{displayName}</p>
          </div>
          <p className="mt-1 text-[11px] text-muted">{PERSONA_LABEL[user?.role ?? ""] ?? user?.role}</p>
          <NavLink to="/app/profile" className="mt-3 flex items-center justify-center gap-2 rounded-md border border-border-soft py-1.5 text-xs text-muted transition hover:border-cyan/40 hover:text-cyan">
            <UserCircle className="h-3.5 w-3.5" /> Account
          </NavLink>
          <button
            onClick={logout}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-border-soft py-1.5 text-xs text-muted transition hover:border-down/40 hover:text-down"
          >
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
        <p className="px-1 text-[10px] text-muted">The dot marks tools suggested for your role.</p>
      </div>
    </aside>
  );
}
