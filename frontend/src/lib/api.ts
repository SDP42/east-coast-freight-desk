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
  cache: "redis" | "in-memory";
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

export interface DisruptionEvent {
  id: number;
  start_date: string;
  end_date: string | null;
  category: string;
  region: string;
  title: string;
  description: string | null;
  impact_score: number | null;
  source_url: string | null;
}

export interface RiskFactor {
  name: string;
  score: number;
  weight: number;
  detail: string;
}

export interface RelevantEvent {
  title: string;
  category: string;
  region: string;
  start_date: string;
  impact_score: number;
  relevance_weight: number;
}

export interface RouteRisk {
  origin_country: string;
  destination_port_name: string;
  composite_score: number;
  risk_label: string;
  factors: RiskFactor[];
  relevant_events: RelevantEvent[];
}

export interface FixtureProjection {
  fixture_number: number;
  date: string;
  forecast_index_value: number;
  projected_spot_rate_usd_per_tonne: number;
}

export interface CoaVsSpotResult {
  index_name: string;
  current_index_value: number;
  current_rate_usd_per_tonne: number;
  coa_rate_usd_per_tonne: number;
  fixtures: FixtureProjection[];
  total_coa_cost_usd: number;
  total_spot_cost_usd: number;
  spot_cost_std_usd: number;
  expected_savings_usd: number;
  recommendation: string;
  rationale: string;
}

export interface DemurrageResult {
  port_name: string;
  vessel_class_name: string;
  actual_turnaround_days: number;
  laytime_allowed_days: number;
  demurrage_days: number;
  demurrage_rate_usd_per_day: number;
  expected_demurrage_usd: number;
  notes: string[];
}

export interface RoiResult {
  index_name: string;
  historical_coefficient_of_variation_pct: number;
  annual_cargo_tonnes: number;
  assumed_freight_usd_per_tonne: number;
  captured_pct: number;
  estimated_annual_savings_usd: number;
  notes: string;
}

export const simulateCoaVsSpot = (body: {
  index_name: string; current_rate_usd_per_tonne: number; cargo_tonnes_per_fixture: number;
  num_fixtures: number; interval_days: number;
}) => api.post<CoaVsSpotResult>("/financial/coa-vs-spot", body).then((r) => r.data);

export const estimateDemurrage = (portId: number, vesselClassId: number, laytimeAllowedDays: number) =>
  api
    .post<DemurrageResult>("/financial/demurrage", { port_id: portId, vessel_class_id: vesselClassId, laytime_allowed_days: laytimeAllowedDays })
    .then((r) => r.data);

export const estimateRoi = (body: { index_name: string; annual_cargo_tonnes: number; assumed_freight_usd_per_tonne: number; captured_pct: number }) =>
  api.post<RoiResult>("/financial/roi", body).then((r) => r.data);

export interface HistoryPoint {
  date: string;
  value: number;
}

export interface RegionSeries {
  index_name: string;
  label: string;
  unit: string;
  date: string;
  value: number;
  change_pct: number | null;
  spark: number[];
}

export interface RegionBoard {
  region: string;
  note: string;
  series: RegionSeries[];
}

export const getHistory = (indexName: string, limit = 500) =>
  api.get<HistoryPoint[]>(`/market/history/${indexName}`, { params: { limit } }).then((r) => r.data);
export const getRegions = () => api.get<RegionBoard[]>("/market/regions").then((r) => r.data);

export interface ForecastPoint {
  date: string;
  value: number;
  lower_ci: number;
  upper_ci: number;
}

export interface ForecastResult {
  index_name: string;
  horizon: number;
  model: string;
  order: [number, number, number];
  is_stationary: boolean;
  adf_pvalue: number;
  forecast: ForecastPoint[];
  backtest_mean_rmse: number;
  backtest_mean_mae: number;
  backtest_mean_mape: number;
  backtest_splits: { split_index: number; train_end: string; rmse: number; mae: number; mape: number }[];
}

export interface EnsembleMetric {
  rmse: number;
  mae: number;
  mape: number;
}

export interface Significance {
  statistic: number;
  p_value: number;
  n: number;
  significant_at_05: boolean;
}

export interface EnsembleResult {
  index_name: string;
  horizon: number;
  arima_order: [number, number, number];
  weights: { arima: number; xgb: number };
  forecast: { date: string; arima_value: number; xgb_value: number; hybrid_value: number }[];
  arima_metrics: EnsembleMetric;
  xgb_metrics: EnsembleMetric;
  hybrid_metrics: EnsembleMetric;
  top_features: { feature: string; mean_abs_shap: number }[];
  hybrid_vs_arima: Significance;
  hybrid_vs_xgb: Significance;
}

export const getForecast = (indexName: string, horizon: number) =>
  api.get<ForecastResult>(`/forecast/${indexName}`, { params: { horizon }, timeout: 60_000 }).then((r) => r.data);
export const getEnsemble = (indexName: string, horizon: number) =>
  api.get<EnsembleResult>(`/forecast/${indexName}/ensemble`, { params: { horizon }, timeout: 120_000 }).then((r) => r.data);

export interface Shock {
  type: "freight_spike" | "port_closure" | "red_sea_closure" | "origin_disruption";
  pct?: number;
  days?: number;
  origin_country?: string;
  extra_distance_nm?: number;
}

export interface OriginDelta {
  origin_country: string;
  baseline_cost_usd: number | null;
  scenario_cost_usd: number | null;
  delta_usd: number | null;
  delta_pct: number | null;
  baseline_rank: number;
  scenario_rank: number;
  compatible: boolean;
}

export interface ReroutePort {
  port_name: string;
  best_origin: string;
  estimated_total_cost_usd: number;
  savings_vs_scenario_best_usd: number;
}

export interface ScenarioResult {
  destination_port_name: string;
  cargo_tonnes: number;
  vessel_class_name: string;
  shocks_applied: string[];
  origins: OriginDelta[];
  baseline_best_origin: string | null;
  scenario_best_origin: string | null;
  best_origin_changed: boolean;
  reroute_alternatives: ReroutePort[];
  summary: string;
}

export const runScenario = (destinationPortId: number, cargoTonnes: number, shocks: Shock[]) =>
  api
    .post<ScenarioResult>("/scenario/run", { destination_port_id: destinationPortId, cargo_tonnes: cargoTonnes, shocks })
    .then((r) => r.data);

export const getDisruptionEvents = () => api.get<DisruptionEvent[]>("/risk/events").then((r) => r.data);
export const getRouteRisk = (originCountry: string, destinationPortId: number) =>
  api
    .get<RouteRisk>("/risk/score", { params: { origin_country: originCountry, destination_port_id: destinationPortId } })
    .then((r) => r.data);

export interface HaldiaSummary {
  facts: Record<string, number>;
  observed: {
    vessels: number; period_start: string | null; period_end: string | null;
    median_cargo_t: number | null; min_cargo_t: number | null; max_cargo_t: number | null;
    median_draft_m: number | null; min_draft_m: number | null; max_draft_m: number | null; median_loa_m: number | null;
    by_importer: Record<string, number>; by_cargo: Record<string, number>;
  };
  recent_vessels: { name: string; loa_m: number | null; draft_m: number | null; cargo: string; tonnage_t: number | null; importer: string; date: string }[];
}
export const getHaldiaSummary = () => api.get<HaldiaSummary>("/haldia/summary").then((r) => r.data);

export interface AskAnswer {
  intent: string; confidence: number; alternatives: { intent: string; confidence: number }[]; entities: Record<string, string | number>;
  text: string; figures: { label: string; value: string }[]; links: { label: string; to: string }[]; assumptions: string[];
}
export interface AssistantInfo {
  model: { algorithm: string; intents: number; training_examples: number; cv_accuracy_mean: number; cv_accuracy_std: number; note: string };
  suggestions: string[];
}
export const askDesk = (question: string) => api.post<AskAnswer>("/assistant/ask", { question }).then((r) => r.data);
export const getAssistantInfo = () => api.get<AssistantInfo>("/assistant/info").then((r) => r.data);
