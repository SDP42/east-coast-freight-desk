import { NavLink } from "react-router-dom";
import { Anchor, LayoutDashboard, TrendingUp, Compass, MapPinned, ShieldAlert } from "lucide-react";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/forecast", label: "Freight Forecast", icon: TrendingUp },
  { to: "/recommendation", label: "Chartering Recommendation", icon: Compass },
  { to: "/ports", label: "Port Compatibility", icon: MapPinned },
  { to: "/risk", label: "Risk & Disruptions", icon: ShieldAlert },
];

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-border-soft bg-ink/80 backdrop-blur-xl min-h-screen p-5 flex flex-col gap-8">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan/20 to-steel/40 border border-cyan/20">
          <Anchor className="h-5 w-5 text-cyan" strokeWidth={1.75} />
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-widest text-cyan/70">SIH 2026</p>
          <h1 className="text-sm font-semibold leading-snug text-white">
            East Coast Freight Desk
          </h1>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                isActive
                  ? "bg-panel-light text-white shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]"
                  : "text-muted hover:bg-panel hover:text-white"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`h-4 w-4 ${isActive ? "text-cyan" : "text-muted group-hover:text-cyan"}`} strokeWidth={1.75} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-lg border border-border-soft bg-panel p-3">
        <p className="text-[10px] uppercase tracking-wide text-muted">Coverage</p>
        <p className="mt-1 text-xs text-ice/90">
          7 East Coast ports · 5 origin countries · 4 vessel classes
        </p>
      </div>
    </aside>
  );
}
