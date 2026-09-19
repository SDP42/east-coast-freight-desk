import { useEffect, useState } from "react";
import { px } from "../lib/scale";
import { Download, Search } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import Sparkline from "../components/Sparkline";
import { Field, Note, PageHeader, Stat, btnCls, inputCls } from "../components/ui";
import { api } from "../lib/api";

interface Series { index_name: string; label: string; unit: string; first: string; last: string; rows: number; source: string }
interface Query { total_matches: number; returned: number; summary: { min: number; max: number; mean: number } | null; rows: { date: string; value: number; unit: string }[] }
interface Search { series: Series[]; events: { title: string; category: string; region: string; date: string }[] }

export default function Explorer() {
  const [series, setSeries] = useState<Series[]>([]);
  const [idx, setIdx] = useState("BPI");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [res, setRes] = useState<Query | null>(null);
  const [q, setQ] = useState("");
  const [found, setFound] = useState<Search | null>(null);

  useEffect(() => { api.get<Series[]>("/data/series").then((r) => setSeries(r.data)); }, []);
  const params = { index_name: idx, start: start || undefined, end: end || undefined, min_value: min || undefined, max_value: max || undefined, limit: 200 };
  useEffect(() => { api.get<Query>("/data/query", { params }).then((r) => setRes(r.data)); }, [idx, start, end, min, max]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (q.trim().length < 2) { setFound(null); return; }
    const t = setTimeout(() => api.get<Search>("/data/search", { params: { q } }).then((r) => setFound(r.data)), 250);
    return () => clearTimeout(t);
  }, [q]);

  const meta = series.find((s) => s.index_name === idx);
  const csvUrl = `${api.defaults.baseURL}/data/export.csv?index_name=${idx}${start ? `&start=${start}` : ""}${end ? `&end=${end}` : ""}`;
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Data explorer" subtitle="Every series the models use. Filter by date and value, search series and documented disruptions, and export what you find." />
      <SpotlightCard>
        <div className="p-6">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search series and disruption events (try 'coal', 'red sea', 'cyclone')" className={inputCls + " !mt-0 pl-9"} />
          </div>
          {found && (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Series ({found.series.length})</p>
                {found.series.map((s) => <button key={s.index_name} onClick={() => { setIdx(s.index_name); setQ(""); }} className="mt-1 block w-full rounded-lg px-2 py-1.5 text-left text-sm text-body hover:bg-panel-light"><b className="text-strong">{s.index_name}</b> · {s.label}</button>)}
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Events ({found.events.length})</p>
                {found.events.map((e) => <p key={e.title} className="mt-1 px-2 py-1.5 text-sm text-body"><b className="text-strong">{e.title}</b><br /><span className="text-xs text-muted">{e.category} · {e.region} · {e.date}</span></p>)}
              </div>
            </div>
          )}
        </div>
      </SpotlightCard>

      <SpotlightCard>
        <div className="p-6">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Field label="Series"><select className={inputCls} value={idx} onChange={(e) => setIdx(e.target.value)}>{series.map((s) => <option key={s.index_name} value={s.index_name}>{s.index_name}: {s.label}</option>)}</select></Field>
            <Field label="From"><input type="date" className={inputCls} value={start} onChange={(e) => setStart(e.target.value)} min={meta?.first} max={meta?.last} /></Field>
            <Field label="To"><input type="date" className={inputCls} value={end} onChange={(e) => setEnd(e.target.value)} min={meta?.first} max={meta?.last} /></Field>
            <Field label="Min value"><input className={inputCls} value={min} onChange={(e) => setMin(e.target.value)} /></Field>
            <Field label="Max value"><input className={inputCls} value={max} onChange={(e) => setMax(e.target.value)} /></Field>
          </div>
          {meta && <p className="mt-2 text-xs text-muted">{meta.rows.toLocaleString()} rows, {meta.first} to {meta.last}. Source: {meta.source}</p>}
          {res && (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <Stat label="Matches" value={res.total_matches.toLocaleString()} />
                <Stat label="Min" value={res.summary ? res.summary.min.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "n/a"} />
                <Stat label="Mean" value={res.summary ? res.summary.mean.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "n/a"} />
                <Stat label="Max" value={res.summary ? res.summary.max.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "n/a"} />
                <div className="flex items-end"><a href={csvUrl} className={btnCls + " flex w-full items-center justify-center gap-2"}><Download className="h-4 w-4" /> CSV</a></div>
              </div>
              {res.rows.length > 1 && <div className="h-16"><Sparkline width={px(640)} height={px(64)} values={[...res.rows].reverse().map((r) => r.value)} up={res.rows[0].value >= res.rows[res.rows.length - 1].value} /></div>}
              <div className="max-h-96 overflow-y-auto rounded-xl border border-border-soft">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-white"><tr className="text-xs text-muted"><th className="px-3 py-2">Date</th><th>Value</th><th>Unit</th></tr></thead>
                  <tbody>{res.rows.map((r) => <tr key={r.date} className="border-t border-border-soft"><td className="px-3 py-1.5 text-strong">{r.date}</td><td>{r.value.toLocaleString()}</td><td className="text-muted">{r.unit}</td></tr>)}</tbody>
                </table>
              </div>
              {res.returned < res.total_matches && <Note>Showing the latest {res.returned} of {res.total_matches.toLocaleString()} matches. The CSV export includes all of them (up to 50,000).</Note>}
            </div>
          )}
        </div>
      </SpotlightCard>
    </div>
  );
}
