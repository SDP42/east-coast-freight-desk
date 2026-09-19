import { useEffect, useRef, useState } from "react";
import { ClipboardPaste, Download, FileUp, Trash2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import LightSelect from "../components/LightSelect";
import Loading from "../components/Loading";
import { Note, PageHeader, Stat, btnCls, errText } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Ship { id: number; vessel: string; dwt: number; open_port: string; open_date: string; broker: string | null; is_sample: boolean; draft_m: number | null }
interface Match { id: number; vessel: string; dwt: number; class: string | null; open_port: string; open_date: string; eta: string | null; days_to_deadline: number | null; status: string; reasons: string[]; is_sample: boolean }
interface MatchRes { total_on_lists: number; suitable_count: number; summary: string; matches: Match[]; lists_stale: boolean; any_sample: boolean; method: string }
const PORTS = ["Paradip", "Visakhapatnam", "Gangavaram", "Dhamra", "Gopalpur", "Haldia"];
const TONE: Record<string, string> = { suitable: "text-up", "unknown timing": "text-warn", "not suitable": "text-down" };

export default function Tonnage() {
  const { can } = useAuth();
  const [ships, setShips] = useState<Ship[]>([]);
  const [port, setPort] = useState("Paradip");
  const [cargo, setCargo] = useState(60000);
  const [days, setDays] = useState(30);
  const [res, setRes] = useState<MatchRes | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  const [paste, setPaste] = useState("");
  const [prev, setPrev] = useState<{ rows: { vessel_name: string; dwt: number; open_port: string; open_date: string; draft_m: number | null; loa_m: number | null; notes: string }[]; unread_lines: string[] } | null>(null);

  const load = () => api.get<{ ships: Ship[] }>("/tonnage").then((r) => setShips(r.data.ships)).catch((e) => setErr(errText(e)));
  const runMatch = () => api.post<MatchRes>("/tonnage/match", { port, cargo_tonnes: cargo, need_by_days: days }).then((r) => { setRes(r.data); setErr(""); }).catch((e) => setErr(errText(e)));
  useEffect(() => { load(); }, []);
  useEffect(() => { const t = setTimeout(runMatch, 300); return () => clearTimeout(t); }, [port, cargo, days, ships.length]); // eslint-disable-line react-hooks/exhaustive-deps

  async function upload(f: File) {
    setBusy(true); setMsg(""); setErr("");
    const fd = new FormData(); fd.append("file", f);
    try { const r = await api.post<{ added: number; skipped_count: number; skipped: { line: number; error: string }[] }>("/tonnage/upload", fd); setMsg(`${r.data.added} ships added` + (r.data.skipped_count ? `, ${r.data.skipped_count} rows skipped (${r.data.skipped.slice(0, 3).map((s) => `line ${s.line}: ${s.error}`).join("; ")})` : "")); await load(); }
    catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  async function parsePaste() { setBusy(true); setErr(""); try { setPrev((await api.post("/tonnage/parse-text", { text: paste })).data); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } }
  async function savePrev() { if (!prev) return; setBusy(true); try { const r = await api.post<{ added: number }>("/tonnage/save-rows", { rows: prev.rows.map((x) => ({ ...x, broker: "Pasted text" })) }); setMsg(`${r.data.added} ships saved from pasted text`); setPrev(null); setPaste(""); await load(); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } }
  async function sample() { setBusy(true); try { await api.post("/tonnage/sample"); setMsg("Sample list loaded (invented ships)"); await load(); } catch (e) { setErr(errText(e)); } finally { setBusy(false); } }
  async function remove(id: number) { try { await api.delete(`/tonnage/${id}`); await load(); } catch (e) { setErr(errText(e)); } }

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Open tonnage" subtitle="Which ships are actually available? Upload the position lists your brokers send (CSV or Excel). The desk matches ships to a cargo by size, berth fit, laycan and ETA. Your own data: nothing is scraped." />
      <div className="space-y-4">
        {can("ledger:write") && (
          <SpotlightCard><div className="flex flex-wrap items-center gap-3 p-5">
            <input ref={file} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <button onClick={() => file.current?.click()} disabled={busy} className={`${btnCls} flex items-center gap-2`}><FileUp className="h-4 w-4" />Upload broker list</button>
            <button onClick={sample} disabled={busy} className="rounded-lg border border-border-soft px-4 py-2 text-sm text-body hover:bg-panel-light">Load a sample list</button>
            <a href="/api/v1/tonnage/template.csv" className="flex items-center gap-1.5 rounded-lg border border-border-soft px-3 py-2 text-xs text-body hover:bg-panel-light"><Download className="h-3.5 w-3.5" />CSV template</a>
            <p className="text-xs text-muted">Columns: vessel_name, dwt, open_port, open_date (required); imo, loa_m, beam_m, draft_m, speed_knots, broker, notes.</p>
          </div></SpotlightCard>
        )}
        {can("ledger:write") && (
          <SpotlightCard><div className="space-y-3 p-5">
            <p className="flex items-center gap-2 text-sm font-semibold text-strong"><ClipboardPaste className="h-4 w-4 text-cyan" />Or paste the broker's email</p>
            <textarea value={paste} onChange={(e) => setPaste(e.target.value)} rows={5} placeholder={"MV AURORA - 82,000 dwt - open Hay Point 22/09 - 14.2 m draft\nM.V. Kestrel 180k dwt, Hay Point, open 25 Sep, LOA 292"} className="w-full rounded-lg border border-border-soft bg-white p-3 font-mono text-xs text-strong outline-none focus:border-cyan focus:ring-4 focus:ring-cyan/10" />
            <button onClick={parsePaste} disabled={busy || paste.trim().length < 8} className={btnCls}>Read it</button>
            {prev && (
              <div className="space-y-2">
                <p className="text-xs text-body">{prev.rows.length} ship(s) read. Check them, then save. {prev.unread_lines.length > 0 && <span className="text-warn">{prev.unread_lines.length} line(s) could not be read (no known loading port, size or date): {prev.unread_lines.slice(0, 3).join(" | ")}</span>}</p>
                {prev.rows.length > 0 && <table className="w-full text-left text-xs"><thead className="text-muted"><tr><th>Vessel</th><th>DWT</th><th>Open port</th><th>Open date</th><th>Draft</th><th>LOA</th></tr></thead><tbody>{prev.rows.map((r, i) => <tr key={i} className="border-t border-border-soft"><td className="py-1 font-medium text-strong">{r.vessel_name}</td><td>{r.dwt.toLocaleString()}</td><td>{r.open_port}</td><td>{r.open_date}</td><td>{r.draft_m ?? ""}</td><td>{r.loa_m ?? ""}</td></tr>)}</tbody></table>}
                {prev.rows.length > 0 && <button onClick={savePrev} disabled={busy} className={btnCls}>Save these ships</button>}
              </div>
            )}
          </div></SpotlightCard>
        )}
        {msg && <Note>{msg}</Note>}{err && <p className="text-xs text-down">{err}</p>}

        <SpotlightCard>
          <div className="grid gap-5 p-5 sm:grid-cols-3">
            <LightSelect label="Discharge port" value={port} options={PORTS} onChange={setPort} width={200} />
            <label className="block text-xs font-medium text-body">Tonnes: {cargo.toLocaleString()}<input type="range" min={20000} max={200000} step={5000} value={cargo} onChange={(e) => setCargo(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
            <label className="block text-xs font-medium text-body">Needed within {days} days<input type="range" min={7} max={90} value={days} onChange={(e) => setDays(Number(e.target.value))} className="mt-3 w-full accent-cyan" /></label>
          </div>
        </SpotlightCard>

        {!res && <Loading label="Matching ships" pattern="sweep" block />}
        {res && (
          <>
            <div className="grid gap-3 sm:grid-cols-3"><Stat label="Ships on your lists" value={res.total_on_lists} /><Stat label="Could carry it in time" value={res.suitable_count} tone={res.suitable_count ? "up" : "down"} /><Stat label="Lists" value={res.lists_stale ? "Over a week old" : res.total_on_lists ? "Fresh" : "None uploaded"} tone={res.lists_stale ? "warn" : undefined} /></div>
            <Note kind={res.suitable_count ? "info" : "warn"}>{res.summary}{res.any_sample ? " (This uses the illustrative sample list of invented ships.)" : ""}</Note>
            {res.matches.length > 0 && (
              <SpotlightCard><div className="max-h-[30rem] overflow-auto p-5">
                <table className="w-full text-left text-xs"><thead className="sticky top-0 bg-white text-muted"><tr><th className="py-1.5">Vessel</th><th>Size</th><th>Open</th><th>ETA</th><th>Verdict</th><th>Why</th></tr></thead>
                  <tbody>{res.matches.map((m) => (
                    <tr key={m.id} className="border-t border-border-soft align-top"><td className="py-2 pr-3 font-medium text-strong">{m.vessel}{m.is_sample && <span className="ml-1 text-[10px] text-muted">(sample)</span>}</td><td className="pr-3">{m.dwt.toLocaleString()} t{m.class ? ` · ${m.class}` : ""}</td><td className="pr-3">{m.open_port}<div className="text-muted">{m.open_date}</div></td><td className="pr-3">{m.eta ?? "n/a"}{m.days_to_deadline !== null && <div className="text-muted">{m.days_to_deadline} d spare</div>}</td><td className={`pr-3 font-semibold ${TONE[m.status]}`}>{m.status}</td><td className="text-body">{m.reasons.join("; ")}</td></tr>
                  ))}</tbody></table>
              </div></SpotlightCard>
            )}
          </>
        )}
        {ships.length > 0 && (
          <SpotlightCard><div className="max-h-72 overflow-auto p-5">
            <h3 className="text-sm font-semibold text-strong">Everything uploaded ({ships.length})</h3>
            <table className="mt-2 w-full text-left text-xs"><tbody>{ships.map((s) => <tr key={s.id} className="border-t border-border-soft"><td className="py-1.5 font-medium text-strong">{s.vessel}</td><td>{s.dwt.toLocaleString()} t</td><td>{s.open_port}</td><td>{s.open_date}</td><td className="text-muted">{s.broker ?? ""}</td><td className="text-right"><button onClick={() => remove(s.id)} aria-label="Remove" className="text-muted hover:text-down"><Trash2 className="h-3.5 w-3.5" /></button></td></tr>)}</tbody></table>
          </div></SpotlightCard>
        )}
        <p className="text-xs text-muted">{res?.method}</p>
      </div>
    </div>
  );
}
