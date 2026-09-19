import { Briefcase, LineChart, Anchor, Landmark, ShieldCheck, type LucideIcon } from "lucide-react";

export interface PersonaView {
  icon: LucideIcon;
  accent: string; // r,g,b for glow
  tagline: string;
  quickActions: { label: string; to: string; hint: string }[];
}

/** Presentation for each persona key returned by the backend. Unknown roles
 * (e.g. accounts created before personas existed) fall back to GENERIC. */
export const PERSONA_VIEW: Record<string, PersonaView> = {
  procurement_manager: {
    icon: Briefcase,
    accent: "14,116,144",
    tagline: "Decide when and how to buy freight.",
    quickActions: [
      { label: "Compare origins for a cargo", to: "/app/recommendation", hint: "Rank all 5 origins by cost and fit" },
      { label: "COA or spot?", to: "/app/financial", hint: "Simulate locking a contract vs staying spot" },
      { label: "Stress-test a decision", to: "/app/scenario", hint: "Freight spike, port closure, Red Sea" },
    ],
  },
  chartering_analyst: {
    icon: LineChart,
    accent: "109,40,217",
    tagline: "Read the market and build the case for a fixture.",
    quickActions: [
      { label: "Watch the live market", to: "/app/markets", hint: "Prices, spikes and regional boards" },
      { label: "Forecast a freight index", to: "/app/forecast", hint: "ARIMA + XGBoost with confidence bands" },
      { label: "Compare origins for a cargo", to: "/app/recommendation", hint: "Cost, transit and market direction" },
    ],
  },
  port_ops: {
    icon: Anchor,
    accent: "180,83,9",
    tagline: "Keep vessels matched to berths and ahead of disruption.",
    quickActions: [
      { label: "Check vessel-to-berth fit", to: "/app/ports", hint: "Draft, LOA, beam and tidal plans" },
      { label: "Score a route's risk", to: "/app/risk", hint: "Disruptions, congestion, volatility" },
      { label: "See the port map", to: "/app/map", hint: "Ports coloured by risk, vessels in transit" },
    ],
  },
  finance_head: {
    icon: Landmark,
    accent: "5,150,105",
    tagline: "Control freight cost exposure and prove the savings.",
    quickActions: [
      { label: "Size the savings", to: "/app/financial", hint: "ROI from better-timed chartering" },
      { label: "Watch INR and freight", to: "/app/markets", hint: "INR per USD alongside the freight indices" },
      { label: "Stress-test the budget", to: "/app/scenario", hint: "What a 50% freight spike does to cost" },
    ],
  },
  admin: {
    icon: ShieldCheck,
    accent: "220,38,38",
    tagline: "Full access across every tool.",
    quickActions: [
      { label: "Watch the live market", to: "/app/markets", hint: "Prices and regional boards" },
      { label: "Compare origins for a cargo", to: "/app/recommendation", hint: "Ranked comparison" },
      { label: "Score a route's risk", to: "/app/risk", hint: "Composite risk score" },
    ],
  },
};

export const GENERIC_VIEW: PersonaView = PERSONA_VIEW.chartering_analyst;

export const personaView = (role: string | undefined): PersonaView => PERSONA_VIEW[role ?? ""] ?? GENERIC_VIEW;

export const PERSONA_LABEL: Record<string, string> = {
  procurement_manager: "Procurement Manager",
  chartering_analyst: "Chartering Analyst",
  port_ops: "Port & Logistics Officer",
  finance_head: "Finance & Treasury",
  admin: "Administrator",
  analyst: "Analyst",
};
