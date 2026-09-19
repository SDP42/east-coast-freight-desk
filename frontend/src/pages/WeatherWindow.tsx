import { useEffect, useState } from "react";
import { CloudRain, Waves, Wind } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LightSelect from "../components/LightSelect";
import Loading from "../components/Loading";
import { Note, PageHeader, Stat, errText } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Day { date: string; wave_m: number; gust_kn: number; rain_mm: number; status: "green" | "amber" | "red"; why: string[] }
interface Res { port: string; headline: string; days: Day[]; lost_working_days: number; best_three_day_window: { from: string; to: string; workable_days: number } | null; note: string }
const PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"];
const CLS = { green: "border-up/30 bg-up/10", amber: "border-warn/30 bg-warn/10", red: "border-down/30 bg-down/10" };

export default function WeatherWindow() {
  const { user } = useAuth();
  const mine = (user as unknown as { assigned_ports?: string[] } | null)?.assigned_ports;
  const [port, setPort] = useState(mine?.[0] ?? "Paradip");
  const [r, setR] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setR(null); setErr(""); api.get<Res>("/weather/window", { params: { port } }).then((x) => setR(x.data)).catch((e) => setErr(errText(e))); }, [port]);
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Weather window" subtitle="Seven days of waves, wind and rain at the port, turned into days when ships can berth and coal can be handled. Live forecast, updated every three hours." />
      <SpotlightCard><div className="p-5"><LightSelect label="Port" value={port} options={mine?.length ? mine : PORTS} onChange={setPort} width={220} /></div></SpotlightCard>
      {err && <p className="mt-3 text-xs text-down">{err}</p>}
      {!r && !err && <Loading label="Reading the forecast" pattern="sweep" block />}
      {r && (
        <div className="mt-4 space-y-4">
          <Note>{r.headline}</Note>
          <div className="grid gap-3 sm:grid-cols-3"><Stat label="Working days lost this week" value={r.lost_working_days} tone={r.lost_working_days >= 1 ? "down" : "up"} /><Stat label="Best three-day window" value={r.best_three_day_window ? `${r.best_three_day_window.from.slice(5)} to ${r.best_three_day_window.to.slice(5)}` : "n/a"} /><Stat label="Days at risk" value={r.days.filter((d) => d.status !== "green").length} /></div>
          <div className="grid gap-2 sm:grid-cols-7">
            {r.days.map((d) => (
              <div key={d.date} className={`rounded-xl border p-3 text-xs ${CLS[d.status]}`}>
                <p className="font-semibold text-strong">{new Date(d.date).toLocaleDateString(undefined, { weekday: "short", day: "numeric" })}</p>
                <p className="mt-2 flex items-center gap-1 text-body"><Waves className="h-3 w-3" />{d.wave_m.toFixed(1)} m</p>
                <p className="flex items-center gap-1 text-body"><Wind className="h-3 w-3" />{d.gust_kn.toFixed(0)} kn</p>
                <p className="flex items-center gap-1 text-body"><CloudRain className="h-3 w-3" />{d.rain_mm.toFixed(0)} mm</p>
                <p className="mt-2 font-medium capitalize text-strong">{d.status}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted">{r.note}</p>
        </div>
      )}
    </div>
  );
}
