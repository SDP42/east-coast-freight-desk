/** Browser-side fallback for the port weather: the same call and the same working-risk rule as backend/app/services/weather.py.
 *  Used only when the server could not reach Open-Meteo (a shared hosting address can be rate-limited); the user's own connection is not. */
export interface Coord { port: string; latitude: number; longitude: number }
export interface Limits { gust_moderate_kmh: number; gust_high_kmh: number; wave_moderate_m: number; wave_high_m: number }
export interface WDay { date: string; gust_max_kmh: number | null; rain_mm: number | null; wave_max_m: number | null; summary: string; working_risk: string }
export interface WPort {
  port: string;
  now: { time: string | null; temperature_c: number | null; wind_kmh: number | null; gust_kmh: number | null; rain_mm: number | null; summary: string; working_risk: string };
  days: WDay[]; worst_day: WDay | null;
}

const WMO: Record<number, string> = { 0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
  61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 81: "Rain showers",
  82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail" };
const RANK: Record<string, number> = { Low: 0, Moderate: 1, High: 2 };

export function workingRisk(gust: number | null | undefined, wave: number | null | undefined, l: Limits): string {
  const g = gust ?? 0, w = wave ?? 0;
  if (g >= l.gust_high_kmh || w >= l.wave_high_m) return "High";
  if (g >= l.gust_moderate_kmh || w >= l.wave_moderate_m) return "Moderate";
  return "Low";
}

async function getJson(url: string): Promise<any[]> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Weather service answered ${r.status}`);
  const j = await r.json();
  return Array.isArray(j) ? j : [j];
}

export async function fetchPortWeather(coords: Coord[], limits: Limits, days = 5): Promise<WPort[]> {
  const lat = coords.map((c) => c.latitude.toFixed(4)).join(","), lon = coords.map((c) => c.longitude.toFixed(4)).join(",");
  const common = `latitude=${lat}&longitude=${lon}&timezone=Asia%2FKolkata&forecast_days=${days}`;
  const fc = await getJson(`https://api.open-meteo.com/v1/forecast?${common}&wind_speed_unit=kmh&current=temperature_2m,wind_speed_10m,wind_gusts_10m,weather_code,precipitation&daily=wind_gusts_10m_max,precipitation_sum,weather_code`);
  let mar: any[] = coords.map(() => ({}));
  try { mar = await getJson(`https://marine-api.open-meteo.com/v1/marine?${common}&daily=wave_height_max`); } catch { /* sea state is optional */ }
  return coords.map((c, i) => {
    const f = fc[i] ?? {}, cur = f.current ?? {}, day = f.daily ?? {}, waves: (number | null)[] = mar[i]?.daily?.wave_height_max ?? [];
    const ds: WDay[] = (day.time ?? []).map((d: string, k: number) => {
      const g = day.wind_gusts_10m_max?.[k] ?? null, w = waves[k] ?? null;
      return { date: d, gust_max_kmh: g, rain_mm: day.precipitation_sum?.[k] ?? null, wave_max_m: w, summary: WMO[day.weather_code?.[k]] ?? "Mixed", working_risk: workingRisk(g, w, limits) };
    });
    const worst = ds.reduce<WDay | null>((a, x) => (a === null || RANK[x.working_risk] > RANK[a.working_risk] ? x : a), null);
    return { port: c.port, days: ds, worst_day: worst,
      now: { time: cur.time ?? null, temperature_c: cur.temperature_2m ?? null, wind_kmh: cur.wind_speed_10m ?? null, gust_kmh: cur.wind_gusts_10m ?? null, rain_mm: cur.precipitation ?? null,
        summary: WMO[cur.weather_code] ?? "Mixed", working_risk: workingRisk(cur.wind_gusts_10m, waves[0], limits) } };
  });
}
