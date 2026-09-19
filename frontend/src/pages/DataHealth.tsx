import { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Loading from "../components/Loading";
import { PageHeader, Stat, errText } from "../components/ui";
import { api } from "../lib/api";

interface S { series: string; label: string; first: string; latest: string; age_days: number; rows: number; status: "fresh" | "ended" | "stale"; source: string; why: string | null }
interface Res { as_of: string; series: S[]; feeds: { feed: string; latest: string | null; rows: number }[]; counts: Record<string, number>; summary: Record<string, number> }

export default function DataHealth() {
  const [d, setD] = useState<Res | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.get<Res>("/admin/data-health").then((r) => setD(r.data)).catch((e) => setErr(errText(e))); }, []);
  const icon = (s: S["status"]) => s === "fresh" ? <CheckCircle2 className="h-4 w-4 text-up" /> : s === "ended" ? <XCircle className="h-4 w-4 text-down" /> : <Clock className="h-4 w-4 text-warn" />;
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Data health" subtitle="How current each dataset is." />
      {err && <p className="text-xs text-down">{err}</p>}
      {!d && !err && <Loading label="Checking datasets" pattern="sweep" block />}
      {d && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Fresh series" value={d.summary.fresh} tone="up" /><Stat label="Ended series" value={d.summary.ended} tone="down" />
            <Stat label="Stale series" value={d.summary.stale} tone={d.summary.stale ? "warn" : undefined} /><Stat label="As of" value={d.as_of} />
          </div>
          <SpotlightCard>
            <div className="overflow-x-auto p-5">
              <table className="w-full text-left text-xs">
                <thead className="text-muted"><tr><th className="py-1.5">Series</th><th>Status</th><th>Latest</th><th>Age</th><th>Rows</th><th>Source and note</th></tr></thead>
                <tbody>
                  {d.series.map((s) => (
                    <tr key={s.series} className="border-t border-border-soft align-top">
                      <td className="py-2 pr-3 font-medium text-strong">{s.label}<div className="font-normal text-muted">{s.series}</div></td>
                      <td className="pr-3"><span className="flex items-center gap-1.5">{icon(s.status)}{s.status}</span></td>
                      <td className="pr-3">{s.latest}</td><td className="pr-3">{s.age_days} d</td><td className="pr-3">{s.rows.toLocaleString()}</td>
                      <td className="text-body">{s.source}{s.why && <div className="text-down">{s.why}</div>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SpotlightCard>
          <div className="grid gap-3 sm:grid-cols-3">
            {d.feeds.map((f) => (<SpotlightCard key={f.feed}><div className="p-4 text-xs"><p className="font-semibold text-strong">{f.feed}</p><p className="mt-1 text-body">Latest {f.latest ?? "none"} · {f.rows.toLocaleString()} rows</p></div></SpotlightCard>))}
          </div>
        </div>
      )}
    </div>
  );
}
