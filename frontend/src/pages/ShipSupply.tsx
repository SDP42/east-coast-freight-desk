import { useEffect, useState } from "react";
import { Anchor, RefreshCw, Ship } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Loading from "../components/Loading";
import { Note, PageHeader, Stat, errText } from "../components/ui";
import { api } from "../lib/api";

interface Row { when: string; movement: string; vessel: string; vessel_type: string; agent: string; from: string; to: string; in_port: boolean }
interface Res {
  enabled?: boolean;
  source: string; url: string; fetched_at: string | null; error: string | null; stale: boolean; bulk_arrivals: number; bulk_departures: number; bulk_in_port_now: number;
  open_ships_arriving: number; coal_cargoes_loaded: number; arriving_from: { port: string; ships: number }[]; signal: string; meaning: string; arrivals: Row[]; limits: string;
}

export default function ShipSupply() {
  const [res, setRes] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  const load = () => { setErr(""); api.get<Res>("/supply/newcastle").then((r) => setRes(r.data)).catch((e) => setErr(errText(e))); };
  useEffect(load, []);
  const tone = res?.signal === "Tonnage thinning" ? "down" : res?.signal === "Tonnage building" ? "up" : "warn";

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Ship supply radar" subtitle="Which ships are actually available? This reads the public daily vessel movements of Newcastle, the world's largest coal port, and shows the bulk carriers arriving to load and leaving loaded." />
      {err && <p className="text-xs text-down">{err}</p>}
      {!res && !err && <Loading label="Reading Newcastle movements" pattern="sweep" block />}
      {res && res.enabled === false && <Note kind="warn">{res.meaning}</Note>}
      {res && res.enabled !== false && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Ships due at coal berths" value={res.open_ships_arriving} />
            <Stat label="Coal ships leaving loaded" value={res.coal_cargoes_loaded} />
            <Stat label="Bulk carriers in port now" value={res.bulk_in_port_now} />
            <Stat label="Supply signal" value={res.signal} tone={tone} />
          </div>
          <Note>{res.meaning}</Note>
          {res.stale && <Note kind="warn">The live page could not be reached; showing the last copy. {res.error}</Note>}
          <div className="grid gap-4 lg:grid-cols-3">
            <SpotlightCard>
              <div className="p-5">
                <h3 className="text-sm font-semibold text-strong">Where arriving ships come from</h3>
                <p className="mt-1 text-xs text-muted">Ships arriving from Asian ports are coming in empty: open tonnage about to load.</p>
                <ul className="mt-3 space-y-1.5 text-sm">
                  {res.arriving_from.map((o) => (
                    <li key={o.port} className="flex items-center justify-between"><span className="flex items-center gap-2 text-body"><Anchor className="h-3.5 w-3.5 text-muted" />{o.port}</span><span className="font-medium text-strong">{o.ships}</span></li>
                  ))}
                </ul>
              </div>
            </SpotlightCard>
            <SpotlightCard className="lg:col-span-2">
              <div className="p-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-strong">Bulk carriers due at Newcastle coal berths</h3>
                  <button onClick={load} className="flex items-center gap-1 text-xs text-muted hover:text-strong"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
                </div>
                <div className="mt-3 max-h-96 overflow-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-white text-muted"><tr><th className="py-1.5 pr-3">When</th><th className="pr-3">Vessel</th><th className="pr-3">Last port</th><th>Berth</th></tr></thead>
                    <tbody>
                      {res.arrivals.map((a, i) => (
                        <tr key={i} className="border-t border-border-soft"><td className="py-1.5 pr-3 text-muted">{a.when}</td><td className="pr-3 font-medium text-strong"><Ship className="mr-1 inline h-3 w-3 text-muted" />{a.vessel}</td><td className="pr-3 text-body">{a.from}</td><td className="text-body">{a.to}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </SpotlightCard>
          </div>
          <p className="text-xs text-muted">Source: <a className="underline" href={res.url} target="_blank" rel="noreferrer">{res.source}</a>. Fetched {res.fetched_at}. {res.limits}</p>
        </div>
      )}
    </div>
  );
}
