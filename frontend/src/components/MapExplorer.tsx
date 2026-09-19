import { useEffect, useMemo, useState } from "react";
import { Anchor, Globe2, Layers, MapPinned, Ship } from "lucide-react";
import SupplyGlobe from "./SupplyGlobe";

/** The supply picture in four views: a 3D globe, a flat map, the loading regions and the East Coast ports. Coastlines are
 *  Natural Earth (public domain); terminal and port limits are the published figures stored with the platform. */
const ORIGINS = [
  { key: "Australia", terminal: "Hay Point / Dalrymple Bay", lat: -21.28, lon: 149.3, draft: "17.5 m", nm: 4700, days: 16.3, note: "Largest supplier: over half of India's coking-coal imports. Capesize up to 200,000 DWT loads here." },
  { key: "Mozambique", terminal: "Nacala (Beira alternative)", lat: -14.47, lon: 40.69, draft: "14 m", nm: 3000, days: 10.4, note: "The growth lane: SAIL's first Benga cargo reached Vizag. Beira is limited to about 12 m, Maputo about 11 m." },
  { key: "United States", terminal: "Hampton Roads (Lamberts Point)", lat: 36.95, lon: -76.33, draft: "15.2 m", nm: 11500, days: 39.9, note: "Loads to 50 ft at high tide; the longest lane, via Suez or the Cape." },
  { key: "Russia", terminal: "Vostochny (Ust-Luga alternative)", lat: 42.72, lon: 133.07, draft: "16 m", nm: 10500, days: 36.5, note: "Capesize up to 190,000 DWT at Vostochny; Ust-Luga on the Baltic is shallower (about 12.7 to 14.55 m)." },
  { key: "Indonesia", terminal: "Balikpapan (Kalimantan)", lat: -1.27, lon: 116.83, draft: "13 m", nm: 2700, days: 9.4, note: "Nearest origin, but mainly thermal coal, and cargoes are often barged out to anchorage." },
];
const PORTS = [
  { name: "Paradip", lat: 20.26, lon: 86.67, draft: "16.5 m", note: "Berthed its first Capesize (152,702 t, part-laden) in Sept 2026; dredging to 18.5 m planned." },
  { name: "Visakhapatnam", lat: 17.69, lon: 83.29, draft: "18.1 m", note: "Deepest of the group; average turnaround 69 h (FY25)." },
  { name: "Gangavaram", lat: 17.62, lon: 83.23, draft: "18 m", note: "Deep-water private port beside Vizag." },
  { name: "Dhamra", lat: 20.79, lon: 86.97, draft: "18 m", note: "Deep-water private port; Capesize capable." },
  { name: "Gopalpur", lat: 19.27, lon: 84.9, draft: "14.2 m", note: "Shallower: no Capesize." },
  { name: "Sagar / Sandheads", lat: 21.05, lon: 88.15, draft: "10.5 m", note: "Anchorage where big ships are lightened before the Hooghly." },
  { name: "Haldia", lat: 22.03, lon: 88.07, draft: "river dock", note: "Impounded dock behind a 330 m by 39 m lock; about 35,000 t reaches the berth." },
];
const VIEWS = [
  { key: "globe", label: "Globe", icon: Globe2 }, { key: "flat", label: "Flat map", icon: Layers }, { key: "regions", label: "Loading regions", icon: Ship }, { key: "ports", label: "East Coast ports", icon: Anchor },
] as const;
type View = (typeof VIEWS)[number]["key"];
const W = 1450, H = 800, LON0 = 20, LON1 = 165, LAT0 = -45, LAT1 = 55;
const px = (lon: number) => ((lon - LON0) / (LON1 - LON0)) * W;
const py = (lat: number) => ((LAT1 - lat) / (LAT1 - LAT0)) * H;

function FlatMap() {
  const [land, setLand] = useState<GeoJSON.FeatureCollection | null>(null);
  const [lanes, setLanes] = useState(true);
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => { fetch("/geo/land.json").then((r) => r.json()).then(setLand).catch(() => undefined); }, []);
  const d = useMemo(() => {
    if (!land) return "";
    const out: string[] = [];
    for (const f of land.features) {
      const g = f.geometry as GeoJSON.MultiPolygon;
      for (const poly of g.coordinates) for (const ring of poly) out.push("M" + ring.map(([x, y]) => `${px(x).toFixed(1)} ${py(y).toFixed(1)}`).join("L") + "Z");
    }
    return out.join("");
  }, [land]);
  const hub = { x: px(86), y: py(19) };
  return (
    <div>
      <div className="mb-2 flex items-center gap-3 text-xs text-muted">
        <label className="flex items-center gap-1.5"><input type="checkbox" checked={lanes} onChange={(e) => setLanes(e.target.checked)} />Sea lanes</label>
        <span>Hover a terminal for its limits.</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-2xl border border-border-soft bg-[#dcecf7]" role="img" aria-label="Flat map of coking-coal loading regions and East Coast ports">
        <path d={d} fill="#f3f5f8" stroke="#a9b6c6" strokeWidth={0.7} />
        {lanes && ORIGINS.map((o) => {
          const x = px(o.lon), y = py(o.lat);
          return <path key={o.key} d={`M${x} ${y} Q${(x + hub.x) / 2} ${Math.min(y, hub.y) - 90} ${hub.x} ${hub.y}`} fill="none" stroke={hover === o.key ? "#d97706" : "#0e7490"} strokeWidth={hover === o.key ? 3 : 1.6} strokeDasharray="7 6" opacity={0.75} />;
        })}
        {PORTS.map((p) => <circle key={p.name} cx={px(p.lon)} cy={py(p.lat)} r={4.5} fill="#d97706" stroke="#fff" strokeWidth={1.5}><title>{`${p.name}: ${p.draft}`}</title></circle>)}
        {ORIGINS.map((o) => (
          <g key={o.key} onMouseEnter={() => setHover(o.key)} onMouseLeave={() => setHover(null)} className="cursor-pointer">
            <circle cx={px(o.lon)} cy={py(o.lat)} r={hover === o.key ? 11 : 8} fill="#0e7490" stroke="#fff" strokeWidth={2} />
            <text x={px(o.lon) + 14} y={py(o.lat) + 4} fontSize={hover === o.key ? 22 : 18} fontWeight={600} fill="#0b2545" stroke="#fff" strokeWidth={4} paintOrder="stroke">{o.key}</text>
            <title>{`${o.terminal}: ${o.draft} draft, ${o.nm.toLocaleString()} nm to Paradip`}</title>
          </g>
        ))}
        <text x={hub.x - 60} y={hub.y + 42} fontSize={20} fontWeight={700} fill="#b45309" stroke="#fff" strokeWidth={4} paintOrder="stroke">East Coast ports</text>
      </svg>
      <p className="mt-1.5 text-[10px] text-muted">Coastline: Natural Earth (public domain). Lanes are hand-drawn for illustration; distances in the Regions tab are planning figures.</p>
    </div>
  );
}

export default function MapExplorer() {
  const [view, setView] = useState<View>("globe");
  return (
    <div className="rounded-[2rem] border border-border-soft bg-white/80 p-4 shadow-[0_40px_100px_-40px_rgba(11,37,69,0.45)] backdrop-blur sm:p-6">
      <div className="flex flex-wrap gap-2" role="tablist">
        {VIEWS.map((v) => (
          <button key={v.key} role="tab" aria-selected={view === v.key} onClick={() => setView(v.key)}
            className={`flex items-center gap-1.5 rounded-full border px-4 py-2 text-xs font-medium transition ${view === v.key ? "border-cyan bg-cyan/10 text-cyan" : "border-border-soft text-body hover:border-cyan/50"}`}>
            <v.icon className="h-3.5 w-3.5" />{v.label}
          </button>
        ))}
      </div>
      <div className="mt-5">
        {view === "globe" && (
          <div className="grid items-center gap-6 lg:grid-cols-[1fr_20rem]">
            <div className="flex justify-center"><SupplyGlobe size={560} /></div>
            <ul className="space-y-2 text-sm">
              {ORIGINS.map((o) => <li key={o.key} className="flex items-center justify-between rounded-xl border border-border-soft bg-white px-3 py-2"><span className="font-medium text-strong">{o.key}</span><span className="text-xs text-muted">{o.nm.toLocaleString()} nm · {o.days} d</span></li>)}
              <li className="px-1 pt-1 text-[11px] text-muted">Drag the globe. Arcs run from each loading terminal to the Bay of Bengal ports.</li>
            </ul>
          </div>
        )}
        {view === "flat" && <FlatMap />}
        {view === "regions" && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {ORIGINS.map((o) => (
              <div key={o.key} className="rounded-2xl border border-border-soft bg-white p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-strong"><MapPinned className="h-4 w-4 text-cyan" />{o.key}</p>
                <p className="mt-1 text-xs font-medium text-body">{o.terminal}</p>
                <div className="mt-2 flex gap-4 text-xs text-muted"><span><b className="text-strong">{o.draft}</b> max draft</span><span><b className="text-strong">{o.nm.toLocaleString()}</b> nm to Paradip</span><span><b className="text-strong">{o.days}</b> days</span></div>
                <p className="mt-2 text-xs leading-relaxed text-body">{o.note}</p>
              </div>
            ))}
            <div className="rounded-2xl border border-dashed border-border-soft p-4 text-xs leading-relaxed text-muted">A ship must fit where it loads and where it discharges. The desk checks both ends, including part-laden calls. Limits are the published figures, with sources, stored with the platform; check the terminal's own notice before fixing.</div>
          </div>
        )}
        {view === "ports" && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {PORTS.map((p) => (
              <div key={p.name} className="rounded-2xl border border-border-soft bg-white p-4">
                <p className="flex items-center justify-between text-sm font-semibold text-strong"><span className="flex items-center gap-2"><Anchor className="h-4 w-4 text-amber" />{p.name}</span><span className="text-xs font-medium text-cyan">{p.draft}</span></p>
                <p className="mt-2 text-xs leading-relaxed text-body">{p.note}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
