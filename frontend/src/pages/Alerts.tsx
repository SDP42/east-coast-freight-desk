import { useCallback, useEffect, useState } from "react";
import { Bell, Trash2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Field, Note, PageHeader, btnCls, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Rule { id: number; name: string; kind: string; param_a: string | null; param_b: string | null; threshold: number; webhook_url: string | null; last_fired_at: string | null }
interface Ev { id: number; rule_id: number; fired_at: string; message: string; delivery: string; is_read: boolean }
interface Data { kinds: Record<string, string>; rules: Rule[]; events: Ev[]; unread: number; channels: { sms_whatsapp: string } }

const TEMPLATES: Record<string, { a?: string; b?: string; th: string; hint: string }> = {
  index_move_pct: { a: "OCEAN_GULF_JAPAN", th: "5", hint: "Series, percent move (monthly)" },
  forecast_change_pct: { a: "OCEAN_GULF_JAPAN", b: "3", th: "-5", hint: "Series, horizon in months, percent (negative = fall)" },
  port_congestion: { a: "Visakhapatnam", th: "7", hint: "Port, score 0-10" },
  route_risk: { a: "Australia", b: "Haldia", th: "6", hint: "Origin, port, score 0-10" },
  model_drift: { a: "BRENT", th: "0", hint: "Series (a daily one)" },
  cyclone_probability: { a: "Paradip", th: "0.2", hint: "Port, probability 0-1" },
};

export default function Alerts() {
  const { user } = useAuth();
  const scoped = user?.port_scope != null;
  const [d, setD] = useState<Data | null>(null);
  const [kind, setKind] = useState(scoped ? "port_congestion" : "index_move_pct");
  const [name, setName] = useState("");
  const [a, setA] = useState("OCEAN_GULF_JAPAN");
  const [b, setB] = useState("");
  const [th, setTh] = useState("3");
  const [hook, setHook] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setD((await api.get<Data>("/alerts")).data), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = TEMPLATES[kind];
    const p = user?.port_scope?.[0];
    setA(scoped && p ? (kind === "route_risk" ? t.a ?? "" : p) : t.a ?? ""); setB(scoped && p && kind === "route_risk" ? p : t.b ?? ""); setTh(t.th);
  }, [kind]); // eslint-disable-line react-hooks/exhaustive-deps

  async function create() {
    setMsg("");
    try { await api.post("/alerts", { name: name || d?.kinds[kind]?.slice(0, 40), kind, param_a: a || null, param_b: b || null, threshold: Number(th), webhook_url: hook || null }); setName(""); setHook(""); await load(); } catch (e) { setMsg(errText(e)); }
  }
  async function check() {
    setBusy(true); setMsg("");
    try { const r = (await api.post<{ fired: number }>("/alerts/check")).data; setMsg(r.fired ? `${r.fired} new alert(s).` : "Nothing new: no rule is triggered, or it already fired in the last 24 hours."); await load(); } catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  }
  async function del(id: number) { await api.delete(`/alerts/${id}`); await load(); }
  async function markRead() { await api.post("/alerts/read"); await load(); }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Alerts" subtitle="Set the conditions that matter and the desk tells you when they are met, in the app or to a webhook of your own." />
      <SpotlightCard>
        <div className="p-6">
          <h2 className="text-sm font-semibold text-strong">New rule</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-6">
            <div className="col-span-2 sm:col-span-2"><Field label="Condition"><select className={inputCls} value={kind} onChange={(e) => setKind(e.target.value)}>{Object.keys(d?.kinds ?? { [kind]: "" }).filter((k) => !scoped || ["port_congestion", "route_risk", "cyclone_probability"].includes(k)).map((k) => <option key={k} value={k}>{k.replace(/_/g, " ")}</option>)}</select></Field></div>
            <Field label="Name"><input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="optional" /></Field>
            <Field label="Parameter 1"><input className={inputCls} value={a} onChange={(e) => setA(e.target.value)} /></Field>
            <Field label="Parameter 2"><input className={inputCls} value={b} onChange={(e) => setB(e.target.value)} /></Field>
            <Field label="Threshold"><input className={inputCls} value={th} onChange={(e) => setTh(e.target.value)} /></Field>
          </div>
          <p className="mt-2 text-xs text-muted">{d?.kinds[kind]}. {TEMPLATES[kind]?.hint}.</p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1"><Field label="Webhook URL (optional, https only)"><input className={inputCls} value={hook} onChange={(e) => setHook(e.target.value)} placeholder="https://hooks.example.com/…" /></Field></div>
            <button className={btnCls} onClick={create}>Create rule</button>
          </div>
          {d && <div className="mt-3"><Note>Channels: in-app and webhook are live. SMS and WhatsApp: {d.channels.sms_whatsapp}.</Note></div>}
        </div>
      </SpotlightCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <SpotlightCard>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-strong">Your rules</h2>
              <button className={btnCls} onClick={check} disabled={busy || !d?.rules.length}>{busy ? "Checking…" : "Check now"}</button>
            </div>
            {msg && <p className="mt-2 text-xs text-body">{msg}</p>}
            {d?.rules.length === 0 && <p className="mt-3 text-sm text-muted">No rules yet.</p>}
            <ul className="mt-3 divide-y divide-border-soft">
              {d?.rules.map((r) => (
                <li key={r.id} className="flex items-start justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-strong">{r.name}</p>
                    <p className="text-xs text-muted">{r.kind.replace(/_/g, " ")} · {[r.param_a, r.param_b].filter(Boolean).join(" → ") || "n/a"} · threshold {r.threshold}{r.webhook_url ? " · webhook" : ""}</p>
                    {r.last_fired_at && <p className="text-[11px] text-muted">Last fired {r.last_fired_at.slice(0, 16)}</p>}
                  </div>
                  <button onClick={() => del(r.id)} className="text-muted hover:text-down" aria-label="Delete rule"><Trash2 className="h-4 w-4" /></button>
                </li>
              ))}
            </ul>
          </div>
        </SpotlightCard>
        <SpotlightCard>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-strong"><Bell className="h-4 w-4 text-cyan" /> Alert feed {d && d.unread > 0 && <span className="rounded-full bg-down px-1.5 text-[10px] text-white">{d.unread}</span>}</h2>
              {d && d.unread > 0 && <button onClick={markRead} className="text-xs text-cyan hover:underline">Mark all read</button>}
            </div>
            {d?.events.length === 0 && <p className="mt-3 text-sm text-muted">Nothing has fired yet. Create a rule and press Check now.</p>}
            <ul className="mt-3 space-y-2">
              {d?.events.map((e) => (
                <li key={e.id} className={`rounded-xl border px-3 py-2 text-sm ${e.is_read ? "border-border-soft text-body" : "border-cyan/40 bg-cyan/5 text-strong"}`}>
                  <p>{e.message}</p>
                  <p className="mt-0.5 text-[11px] text-muted">{e.fired_at.slice(0, 16)} · {e.delivery}</p>
                </li>
              ))}
            </ul>
          </div>
        </SpotlightCard>
      </div>
    </div>
  );
}
