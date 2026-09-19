import {
  LayoutDashboard, TrendingUp, Compass, MapPinned, ShieldAlert, Calculator, FlaskConical, Activity, Map, MessageSquareText, KeyRound, Leaf, Radar,
  Database, BookLock, Bell, Gauge, Globe2, Mountain, Dices, Brain, FileText, Zap, type LucideIcon,
} from "lucide-react";

export interface NavLinkDef { to: string; key: string; label: string; icon: LucideIcon; hint?: string }
export interface NavGroup { title: string; links: NavLinkDef[] }

export const NAV_GROUPS: NavGroup[] = [
  { title: "Decide", links: [
    { to: "/app", key: "overview", label: "Overview", icon: LayoutDashboard },
    { to: "/app/ask", key: "ask", label: "Ask the Desk", icon: MessageSquareText, hint: "Chat or speak a question" },
    { to: "/app/recommendation", key: "recommendation", label: "Chartering Recommendation", icon: Compass },
    { to: "/app/financial", key: "financial", label: "Financial Tools", icon: Calculator },
    { to: "/app/voyage", key: "voyage", label: "Voyage Economics", icon: Leaf },
    { to: "/app/scenario", key: "scenario", label: "Scenario Sandbox", icon: FlaskConical },
    { to: "/app/risklab", key: "risklab", label: "Risk Lab", icon: Dices, hint: "3D forecast fan and cost at risk" },
  ] },
  { title: "Analyse", links: [
    { to: "/app/markets", key: "markets", label: "Markets", icon: Activity },
    { to: "/app/live", key: "live", label: "Live Desk", icon: Zap, hint: "Minute-by-minute ticks (simulated)" },
    { to: "/app/forecast", key: "forecast", label: "Freight Forecast", icon: TrendingUp },
    { to: "/app/lab", key: "lab", label: "Model Lab", icon: Brain, hint: "Deep learning vs classical models" },
    { to: "/app/terrain", key: "terrain", label: "Market Terrain", icon: Mountain, hint: "3D landscape of the series" },
    { to: "/app/ports", key: "ports", label: "Port Compatibility", icon: MapPinned },
    { to: "/app/signals", key: "signals", label: "Port Signals", icon: Radar },
    { to: "/app/globe", key: "globe", label: "Trade Globe", icon: Globe2, hint: "3D lanes and chokepoints" },
    { to: "/app/risk", key: "risk", label: "Risk & Disruptions", icon: ShieldAlert },
    { to: "/app/map", key: "map", label: "Port Map", icon: Map },
    { to: "/app/explorer", key: "explorer", label: "Data Explorer", icon: Database },
  ] },
  { title: "Operate", links: [
    { to: "/app/ledger", key: "ledger", label: "Fixture Ledger", icon: BookLock },
    { to: "/app/alerts", key: "alerts", label: "Alerts", icon: Bell },
    { to: "/app/monitor", key: "monitor", label: "Model Monitor", icon: Gauge },
    { to: "/app/report", key: "report", label: "Board Pack", icon: FileText, hint: "Print-ready briefing" },
    { to: "/app/access", key: "access", label: "Access & Audit", icon: KeyRound },
  ] },
];
