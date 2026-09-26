import { useEffect, useState } from "react";
import { CloudRain, Waves, Wind } from "lucide-react";
import SpotlightCard from "./SpotlightCard";
import Loading from "./Loading";
import { Note, errText, tone } from "./ui";
import { api } from "../lib/api";
import { fetchPortWeather, type Coord, type Limits } from "../lib/weather";

interface Day { date: string; gust_max_kmh: number | null; rain_mm: number | null; wave_max_m: number | null; summary: string; working_risk: string }
interface P { port: string; now: { time: string | null; temperature_c: number | null; wind_kmh: number | null; gust_kmh: number | null; rain_mm: number | null; summary: string; working_risk: string }; days: Day[]; worst_day: Day | null }
interface Res { available: boolean; ports: P[]; note?: string; source?: string; fetched_at?: string; limits?: Limits; coords?: Coord[]; days?: number; direct?: boolean }

const cls = (t: "up" | "down" | "warn") => (t === "up" ? "border-up/30 bg-up/10 text-up" : t === "down" ? "border-down/30 bg-down/10 text-down" : "border-warn/30 bg-warn/10 text-warn");
const dayName = (d: string) => new Date(d + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });

/** Live weather and sea state at the discharge ports, with a simple working-risk label per day (Open-Meteo). */
export default function PortWeather() {
  const [d, setD] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get<Res>("/weather/ports").then(async (r) => {
      const v = r.data;
      // The server could not reach the weather service (a shared host can be rate-limited): ask it from this browser instead.
      if (!v.available && v.coords?.length && v.limits) {
        try {
          const ports = await fetchPortWeather(v.coords, v.limits, v.days ?? 5);
          setD({ available: true, ports: ports as P[], limits: v.limits, direct: true, source: "Open-Meteo (forecast and marine APIs), CC BY 4.0, fetched from your browser", fetched_at: new Date().toISOString(),
            note: "Working risk is a simple rule on gusts and wave height, not an official forecast. Wave data is offshore, so it can overstate river ports." });
          return;
        } catch { /* fall through to the server's message */ }
      }
      setD(v);
    }).catch((e) => setErr(errText(e)));
  }, []);
  if (err) return <Note kind="warn">{err}</Note>;
  if (!d) return <Loading label="Fetching port weather" />;
  if (!d.available) return <Note kind="warn">{d.note}</Note>;
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted">Live wind, rain and wave height at each discharge port for the next five days. Working risk flags gusts of 40 km/h or more, or waves of 1.5 m or more, as Moderate, and 55 km/h or 2.5 m as High: a simple rule, not an official forecast.</p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {d.ports.map((p) => (
          <SpotlightCard key={p.port}>
            <div className="p-5">
              <div className="flex items-start justify-between gap-2">
                <div><h3 className="text-sm font-semibold text-strong">{p.port}</h3><p className="text-xs text-muted">{p.now.summary}{p.now.temperature_c !== null && <> · {p.now.temperature_c.toFixed(0)} °C</>}</p></div>
                <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls(tone(p.now.working_risk))}`}>{p.now.working_risk} now</span>
              </div>
              <div className="mt-3 flex gap-4 text-xs text-strong">
                <span className="inline-flex items-center gap-1"><Wind className="h-3.5 w-3.5 text-cyan" />{p.now.wind_kmh?.toFixed(0) ?? "–"} km/h, gusts {p.now.gust_kmh?.toFixed(0) ?? "–"}</span>
                <span className="inline-flex items-center gap-1"><CloudRain className="h-3.5 w-3.5 text-cyan" />{p.now.rain_mm ?? 0} mm</span>
              </div>
              <div className="mt-3 grid grid-cols-5 gap-1.5">
                {p.days.map((x) => (
                  <div key={x.date} className={`rounded-lg border px-1 py-1.5 text-center ${cls(tone(x.working_risk))}`} title={`${x.summary}. Gusts up to ${x.gust_max_kmh ?? "–"} km/h, rain ${x.rain_mm ?? 0} mm${x.wave_max_m !== null ? `, waves up to ${x.wave_max_m} m` : ""}`}>
                    <div className="text-[10px] font-medium">{dayName(x.date)}</div>
                    <div className="text-[11px] font-semibold tabular-nums">{x.gust_max_kmh?.toFixed(0) ?? "–"}</div>
                    <div className="inline-flex items-center gap-0.5 text-[10px]"><Waves className="h-2.5 w-2.5" />{x.wave_max_m !== null ? x.wave_max_m.toFixed(1) : "–"}</div>
                  </div>
                ))}
              </div>
              <p className="mt-2 text-[10px] text-muted">Each day: top gust (km/h) and top wave (m). Hover for detail.</p>
            </div>
          </SpotlightCard>
        ))}
      </div>
      <p className="text-[11px] text-muted">{d.source}. {d.note} Fetched {d.fetched_at?.slice(11, 16)} UTC{d.direct ? "." : " and cached for 30 minutes."}</p>
    </div>
  );
}
