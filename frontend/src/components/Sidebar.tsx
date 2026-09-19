import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { api } from "../lib/api";
import { Anchor, LogOut, UserCircle } from "lucide-react";
import { useAuth } from "../lib/auth";
import { NAV_GROUPS as groups } from "../lib/nav";
import { PERSONA_LABEL, personaView, routeAllowed } from "../lib/personas";

export default function Sidebar() {
  const { user, logout, can } = useAuth();
  const view = personaView(user?.persona ?? user?.role);
  const focus = new Set(
    { procurement_manager: ["ask", "recommendation", "financial"], chartering_analyst: ["markets", "forecast", "recommendation"],
      port_ops: ["ports", "risk", "map"], finance_head: ["financial", "markets", "scenario"] }[user?.persona ?? ""] ?? [],
  );
  const displayName = user?.full_name || user?.email || "";
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    const load = () => api.get<{ unread: number }>("/alerts").then((r) => setUnread(r.data.unread)).catch(() => undefined);
    load();
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col gap-4 border-r border-border-soft bg-ink/80 p-5 backdrop-blur-xl">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-cyan/20 bg-gradient-to-br from-cyan/20 to-steel/40">
          <Anchor className="h-5 w-5 text-cyan" strokeWidth={1.75} />
        </div>
        <div>
          <p className="text-[10px] font-medium uppercase tracking-widest text-cyan/70">SIH 2026</p>
          <h1 className="text-sm font-semibold leading-snug text-strong">East Coast Freight Desk</h1>
        </div>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
        {groups.map((g) => ({ ...g, links: g.links.filter((l) => routeAllowed(l.to, can)) })).filter((g) => g.links.length > 0).map((g) => (
          <div key={g.title}>
            <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted/80">{g.title}</p>
            <div className="flex flex-col gap-0.5">
              {g.links.map(({ to, key, label, icon: Icon }) => (
                <NavLink
                  key={to} to={to} end={to === "/app"}
                  className={({ isActive }) => `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all ${isActive ? "bg-panel-light text-strong shadow-[inset_0_0_0_1px_rgba(14,116,144,0.25)]" : "text-muted hover:bg-panel-light hover:text-strong"}`}
                >
                  {({ isActive }) => (
                    <>
                      <Icon className={`h-4 w-4 ${isActive ? "text-cyan" : "text-muted group-hover:text-cyan"}`} strokeWidth={1.75} />
                      <span className="flex-1">{label}</span>
                      {key === "alerts" && unread > 0 && <span className="rounded-full bg-down px-1.5 text-[10px] font-semibold text-white">{unread}</span>}
                      {focus.has(key) && <span title={`Suggested for ${PERSONA_LABEL[user?.role ?? ""] ?? "you"}`} className="h-1.5 w-1.5 rounded-full bg-cyan" />}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="space-y-3">
        <div className="rounded-lg border border-border-soft bg-panel p-3">
          <div className="flex items-center gap-2">
            <view.icon className="h-4 w-4 shrink-0" style={{ color: `rgb(${view.accent})` }} strokeWidth={1.75} />
            <p className="truncate text-xs font-medium text-strong">{displayName}</p>
          </div>
          <p className="mt-1 flex items-center gap-1.5 text-[11px] text-muted">
            {user?.role_label ?? PERSONA_LABEL[user?.role ?? ""]}
            <span className="flex gap-0.5" title={`Authority level ${user?.level ?? 0} of 5`}>
              {[1, 2, 3, 4, 5].map((n) => <span key={n} className={`h-1.5 w-1.5 rounded-full ${n <= (user?.level ?? 0) ? "bg-cyan" : "bg-border-soft"}`} />)}
            </span>
          </p>
          {user?.port_scope && <p className="mt-1 text-[10px] text-amber">Ports: {user.port_scope.join(", ") || "none assigned"}</p>}
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
        <p className="px-1 text-[10px] text-muted">The dot marks tools suggested for your role. Press <kbd className="rounded border border-border-soft px-1">Ctrl/⌘ K</kbd> to jump anywhere.</p>
      </div>
    </aside>
  );
}
