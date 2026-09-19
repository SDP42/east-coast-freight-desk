import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CornerDownLeft, MessageSquareText, Search } from "lucide-react";
import { NAV_GROUPS } from "../lib/nav";
import { useFeatures } from "../lib/features";
import { routeAllowed } from "../lib/personas";
import { useAuth } from "../lib/auth";

/** Cmd/Ctrl+K: jump to any page you may open, or send what you typed to the assistant. */
export default function CommandPalette() {
  const features = useFeatures();
  const { can } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); setQ(""); setCursor(0); }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, []);
  useEffect(() => { if (open) setTimeout(() => input.current?.focus(), 30); }, [open]);

  const items = useMemo(() => {
    const all = NAV_GROUPS.flatMap((g) => g.links.filter((l) => routeAllowed(l.to, can) && (l.key !== "live" || features.simulated)).map((l) => ({ ...l, group: g.title })));
    const t = q.trim().toLowerCase();
    return t ? all.filter((l) => (l.label + " " + (l.hint ?? "") + " " + l.group).toLowerCase().includes(t)) : all;
  }, [q, can, features.simulated]);
  const askRow = q.trim().length > 2 && can("assistant:use");
  const total = items.length + (askRow ? 1 : 0);

  function go(i: number) {
    if (i < items.length) nav(items[i].to);
    else if (askRow) nav(`/app/ask?q=${encodeURIComponent(q.trim())}`);
    setOpen(false);
  }
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-strong/30 p-4 pt-[12vh] backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-border-soft bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-border-soft px-4 py-3">
          <Search className="h-4 w-4 text-muted" />
          <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setCursor(0); }} placeholder="Go to a page, or ask a question…"
            onKeyDown={(e) => { if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(total - 1, c + 1)); } else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(0, c - 1)); } else if (e.key === "Enter") go(cursor); }}
            className="flex-1 bg-transparent text-sm text-strong outline-none placeholder:text-slate-400" />
          <kbd className="rounded border border-border-soft px-1.5 py-0.5 text-[10px] text-muted">esc</kbd>
        </div>
        <ul className="max-h-[50vh] overflow-y-auto p-2">
          {items.map((l, i) => (
            <li key={l.to}>
              <button onMouseEnter={() => setCursor(i)} onClick={() => go(i)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm ${cursor === i ? "bg-panel-light" : ""}`}>
                <l.icon className="h-4 w-4 text-cyan" />
                <span className="flex-1"><span className="text-strong">{l.label}</span>{l.hint && <span className="ml-2 text-xs text-muted">{l.hint}</span>}</span>
                <span className="text-[10px] uppercase tracking-wide text-muted">{l.group}</span>
              </button>
            </li>
          ))}
          {askRow && (
            <li>
              <button onMouseEnter={() => setCursor(items.length)} onClick={() => go(items.length)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm ${cursor === items.length ? "bg-panel-light" : ""}`}>
                <MessageSquareText className="h-4 w-4 text-violet-600" /><span className="flex-1 text-strong">Ask the desk: <span className="text-body">"{q.trim()}"</span></span><CornerDownLeft className="h-3.5 w-3.5 text-muted" />
              </button>
            </li>
          )}
          {total === 0 && <li className="px-3 py-6 text-center text-sm text-muted">Nothing matches.</li>}
        </ul>
      </div>
    </div>
  );
}
