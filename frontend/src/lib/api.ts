import axios from "axios";

// In dev, Vite proxies /api to the local FastAPI backend (see vite.config.ts).
// In production this should point at the deployed Render backend URL via an
// env var (VITE_API_BASE_URL) — set that in Vercel's project settings.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 20_000,
});

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "up" | "down";
  cache: "up" | "down";
  latency_ms: number;
}

export async function getHealth(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>("/health");
  return data;
}

export interface Port {
  id: number;
  name: string;
  country: string;
  is_destination: boolean;
  max_draft_m: number | null;
  max_loa_m: number | null;
  max_beam_m: number | null;
  tidal_restricted: boolean;
  max_vessels_per_tide: number | null;
  annual_capacity_mtpa: number | null;
  avg_turnaround_hours: number | null;
  notes: string | null;
}

export interface VesselClass {
  id: number;
  name: string;
  dwt_min: number;
  dwt_max: number;
  typical_loa_m: number | null;
  typical_beam_m: number | null;
  typical_draft_m: number | null;
}

export interface MatrixRow {
  port: string;
  port_id: number;
  vessel_classes: Record<string, boolean>;
}

export interface ConstraintCheck {
  name: string;
  required: number | null;
  available: number | null;
  passed: boolean;
  detail: string;
}

export interface TidalLoadPlan {
  tonnes_per_cycle: number;
  cycles_required: number;
  days_required: number;
  max_vessels_per_tide: number | null;
}

export interface CompatibilityResult {
  compatible: boolean;
  port_name: string;
  vessel_class_name: string;
  checks: ConstraintCheck[];
  tidal_plan: TidalLoadPlan | null;
  notes: string[];
}

export interface TickerItem {
  index_name: string;
  label: string;
  unit: string;
  date: string;
  value: number;
  prev_date: string | null;
  prev_value: number | null;
  change: number | null;
  change_pct: number | null;
}

export const getTicker = () => api.get<TickerItem[]>("/market/ticker").then((r) => r.data);

export const getPorts = () => api.get<Port[]>("/compatibility/ports").then((r) => r.data);
export const getVesselClasses = () => api.get<VesselClass[]>("/compatibility/vessel-classes").then((r) => r.data);
export const getMatrix = () => api.get<MatrixRow[]>("/compatibility/matrix").then((r) => r.data);
export const checkCompatibility = (portId: number, vesselClassId: number, cargoTonnes?: number) =>
  api
    .get<CompatibilityResult>("/compatibility/check", {
      params: { port_id: portId, vessel_class_id: vesselClassId, cargo_tonnes: cargoTonnes },
    })
    .then((r) => r.data);

export interface OriginRecommendation {
  origin_country: string;
  route_id: number | null;
  distance_nm: number | null;
  typical_transit_days: number | null;
  vessel_class_name: string;
  compatibility: CompatibilityResult;
  estimated_freight_usd_per_tonne: number | null;
  estimated_total_cost_usd: number | null;
  market_index_used: string | null;
  market_index_forecast_value: number | null;
  market_index_forecast_change_pct: number | null;
  rank: number | null;
  notes: string[];
}

export interface RecommendationResponse {
  destination_port_name: string;
  cargo_tonnes: number;
  recommendations: OriginRecommendation[];
  methodology_note: string;
}

export const compareOrigins = (destinationPortId: number, cargoTonnes: number, originCountries?: string[]) =>
  api
    .post<RecommendationResponse>("/recommendation/compare", {
      destination_port_id: destinationPortId,
      cargo_tonnes: cargoTonnes,
      origin_countries: originCountries ?? null,
    })
    .then((r) => r.data);
