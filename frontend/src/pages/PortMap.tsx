import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { motion } from "framer-motion";
import { Info, Ship, Waves } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { api } from "../lib/api";

interface MapPort {
  id: number; name: string; latitude: number; longitude: number; is_destination: boolean; country: string;
  max_draft_m: number | null; max_loa_m: number | null; tidal_restricted: boolean;
  annual_capacity_mtpa: number | null; avg_turnaround_hours: number | null;
  congestion_score: number; congestion_label: string; classes_accepted: string[]; simulated_queue: number;
}
interface MapRoute { key: string; origin_country: string; destination: string; transit_days: number; waypoints: [number, number][] }
interface MapVessel { id: number; name: string; vessel_class: string; route_key: string; progress: number; progress_per_second: number }
interface Overview { ports: MapPort[]; routes: MapRoute[]; vessels: MapVessel[]; note: string }

const RISK_COLOR: Record<string, string> = { Low: "#059669", Moderate: "#d97706", High: "#dc2626", Severe: "#dc2626" };
const CLASS_COLOR: Record<string, string> = { Capesize: "#7c3aed", Panamax: "#0e7490", Supramax: "#d97706", Handysize: "#059669" };

function positionAlong(waypoints: [number, number][], t: number): [number, number] {
  const seg = waypoints.slice(1).map((p, i) => Math.hypot(p[0] - waypoints[i][0], p[1] - waypoints[i][1]));
  const total = seg.reduce((a, b) => a + b, 0);
  let target = Math.min(Math.max(t, 0), 1) * total;
  for (let i = 0; i < seg.length; i++) {
    if (target <= seg[i]) {
      const f = seg[i] === 0 ? 0 : target / seg[i];
      return [waypoints[i][0] + (waypoints[i + 1][0] - waypoints[i][0]) * f, waypoints[i][1] + (waypoints[i + 1][1] - waypoints[i][1]) * f];
    }
    target -= seg[i];
  }
  return waypoints[waypoints.length - 1];
}

const vesselIcon = (color: string) =>
  L.divIcon({
    className: "",
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid #f3f7fb;box-shadow:0 0 8px ${color}"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, 7, { duration: 1.2 });
  }, [target, map]);
  return null;
}

export default function PortMap() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState(false);
  const [fetchedAt, setFetchedAt] = useState(Date.now());
  const [now, setNow] = useState(Date.now());
  const [focus, setFocus] = useState<[number, number] | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api.get<Overview>("/map/overview").then((r) => {
        if (cancelled) return;
        setData(r.data);
        setFetchedAt(Date.now());
        setError(false);
      }).catch(() => !cancelled && setError(true));
    load();
    const id = setInterval(load, 30_000); // re-sync simulated positions and queues
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  const routeByKey = useMemo(() => new Map(data?.routes.map((r) => [r.key, r])), [data]);
  const destinations = data?.ports.filter((p) => p.is_destination) ?? [];
  const origins = data?.ports.filter((p) => !p.is_destination) ?? [];
  const elapsed = (now - fetchedAt) / 1000;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-strong">Port Map</h1>
        <p className="mt-1 flex items-start gap-1.5 text-xs text-muted">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {data?.note ?? "Loading map data…"}
        </p>
      </motion.div>

      {error && <p className="text-sm text-down">Could not load map data — is the backend running?</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="overflow-hidden rounded-xl border border-border-soft lg:col-span-2" style={{ height: 560 }}>
          <MapContainer center={[14, 88]} zoom={5} style={{ height: "100%", width: "100%", background: "#f3f7fb" }} scrollWheelZoom>
            {/* Keyless OpenStreetMap tiles (CARTO's free tiles now require an API key),
                shown as-is on the light theme. */}
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FlyTo target={focus} />

            {data?.routes.map((r) => (
              <Polyline key={r.key} positions={r.waypoints} pathOptions={{ color: "#0e7490", weight: 1, opacity: 0.18, dashArray: "4 6" }} />
            ))}

            {origins.map((o) => (
              <CircleMarker key={o.id} center={[o.latitude, o.longitude]} radius={4} pathOptions={{ color: "#64748b", fillColor: "#64748b", fillOpacity: 0.7, weight: 1 }}>
                <Tooltip>{o.country} export terminal (representative)</Tooltip>
              </CircleMarker>
            ))}

            {destinations.map((p) => {
              const color = RISK_COLOR[p.congestion_label] ?? "#64748b";
              const radius = 6 + Math.min(8, (p.annual_capacity_mtpa ?? 20) / 15);
              return (
                <CircleMarker key={p.id} center={[p.latitude, p.longitude]} radius={radius} pathOptions={{ color, fillColor: color, fillOpacity: 0.35, weight: 2 }}>
                  <Popup>
                    <div style={{ minWidth: 190, color: "#111827", fontSize: 12 }}>
                      <strong style={{ fontSize: 13 }}>{p.name}</strong>
                      <div>Congestion: {p.congestion_label} ({p.congestion_score}/10)</div>
                      <div>Max draft: {p.max_draft_m ? `${p.max_draft_m} m` : "tide-dependent"}</div>
                      <div>Turnaround: {p.avg_turnaround_hours ? `${p.avg_turnaround_hours} h` : "no data on file"}</div>
                      <div>Accepts: {p.classes_accepted.join(", ") || "—"}</div>
                      {p.tidal_restricted && <div>Tide-restricted port</div>}
                      <div>Simulated queue: {p.simulated_queue} vessels</div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}

            {data?.vessels.map((v) => {
              const route = routeByKey.get(v.route_key);
              if (!route) return null;
              const pos = positionAlong(route.waypoints, (v.progress + v.progress_per_second * elapsed) % 1);
              return (
                <Marker key={v.id} position={pos} icon={vesselIcon(CLASS_COLOR[v.vessel_class] ?? "#0e7490")}>
                  <Tooltip>{v.name} · {v.vessel_class} · {route.origin_country} → {route.destination} (simulated)</Tooltip>
                </Marker>
              );
            })}
          </MapContainer>
        </div>

        <div className="space-y-4">
          <SpotlightCard>
            <div className="p-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Waves className="h-4 w-4 text-cyan" /> East Coast ports</h2>
              <div className="mt-3 space-y-1.5">
                {[...destinations].sort((a, b) => b.congestion_score - a.congestion_score).map((p) => {
                  const color = RISK_COLOR[p.congestion_label] ?? "#64748b";
                  return (
                    <button key={p.id} onClick={() => setFocus([p.latitude, p.longitude])} className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition hover:bg-panel-light/60">
                      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-medium text-strong">{p.name}</span>
                        <span className="block text-[10px] text-muted">{p.congestion_label} · {p.classes_accepted.length ? p.classes_accepted[p.classes_accepted.length - 1] + " max" : "—"}</span>
                      </span>
                      <span className="text-right">
                        <span className="block text-xs tabular-nums text-body">{p.simulated_queue}</span>
                        <span className="block text-[10px] text-muted">queued</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </SpotlightCard>

          <SpotlightCard>
            <div className="p-4 text-xs">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Ship className="h-4 w-4 text-cyan" /> Legend</h2>
              <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-muted">
                {Object.entries(CLASS_COLOR).map(([k, c]) => (
                  <span key={k} className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{k}</span>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 text-muted">
                {Object.entries(RISK_COLOR).map(([k, c]) => (
                  <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: c }} />{k}</span>
                ))}
              </div>
              <p className="mt-3 text-[10px] leading-relaxed text-muted">
                Ring colour is the port's congestion score (real); ring size is annual capacity. Dots are simulated vessels; "queued" is a simulated anchorage count.
              </p>
            </div>
          </SpotlightCard>
        </div>
      </div>
    </div>
  );
}
