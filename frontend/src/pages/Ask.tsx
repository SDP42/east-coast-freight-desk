import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, Bot, Sparkles, User as UserIcon } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { askDesk, getAssistantInfo, type AskAnswer, type AssistantInfo } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Turn { id: number; question: string; answer?: AskAnswer; error?: string }

const INTENT_LABEL: Record<string, string> = {
  market_now: "Market snapshot", forecast: "Forecast", recommend_origin: "Origin comparison", port_fit: "Berth fit", risk: "Route risk",
  congestion: "Port congestion", haldia: "Haldia operations", coa_vs_spot: "COA vs spot", demand: "SAIL demand", data_sources: "Data & accuracy", help: "Help", unclear: "Unclear",
};

export default function Ask() {
  const { user } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<AssistantInfo | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => { getAssistantInfo().then(setInfo).catch(() => setInfo(null)); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns, busy]);

  async function send(question: string) {
    const q = question.trim();
    if (q.length < 2 || busy) return;
    const id = nextId.current++;
    setTurns((t) => [...t, { id, question: q }]);
    setText("");
    setBusy(true);
    try {
      const answer = await askDesk(q);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, answer } : x)));
    } catch {
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: "The desk could not answer that just now. Is the backend running?" } : x)));
    } finally {
      setBusy(false);
    }
  }

  const submit = (e: FormEvent) => { e.preventDefault(); send(text); };
  const firstName = (user?.full_name || "").split(" ")[0];

  return (
    <div className="mx-auto flex h-[calc(100vh-7.5rem)] max-w-4xl flex-col">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-strong"><Sparkles className="h-5 w-5 text-cyan" /> Ask the Freight Desk</h1>
        <p className="mt-1 text-sm text-muted">
          Plain-English questions, answered from this platform's own engines and data. A local intent model picks the engine; nothing leaves your deployment.
        </p>
      </div>

      <div className="mt-5 flex-1 space-y-5 overflow-y-auto pr-1">
        {turns.length === 0 && (
          <SpotlightCard>
            <div className="p-6">
              <p className="text-sm font-semibold text-strong">{firstName ? `Hello ${firstName}. ` : ""}What would you like to know?</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(info?.suggestions ?? []).map((s) => (
                  <button key={s} onClick={() => send(s)} className="rounded-full border border-border-soft bg-white px-3.5 py-1.5 text-xs text-body transition hover:border-cyan hover:text-cyan">{s}</button>
                ))}
              </div>
              {info && (
                <p className="mt-5 text-[11px] leading-relaxed text-muted">
                  Model: {info.model.algorithm}; {info.model.intents} intents, {info.model.training_examples} training examples. Held-out accuracy on our own hand-written questions:
                  {" "}{(info.model.cv_accuracy_mean * 100).toFixed(0)}% ± {(info.model.cv_accuracy_std * 100).toFixed(0)}%. {info.model.note}
                </p>
              )}
            </div>
          </SpotlightCard>
        )}

        <AnimatePresence initial={false}>
          {turns.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              <div className="flex justify-end gap-2">
                <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-strong px-4 py-2.5 text-sm text-on-accent">{t.question}</div>
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-panel-light"><UserIcon className="h-3.5 w-3.5 text-body" /></div>
              </div>
              <div className="flex gap-2">
                <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-cyan/10"><Bot className="h-3.5 w-3.5 text-cyan" /></div>
                <div className="max-w-[88%] rounded-2xl rounded-tl-sm border border-border-soft bg-white/95 px-4 py-3 shadow-sm">
                  {t.error && <p className="text-sm text-down">{t.error}</p>}
                  {!t.answer && !t.error && (
                    <div className="flex gap-1 py-1">{[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${i * 0.15}s` }} />)}</div>
                  )}
                  {t.answer && (
                    <>
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-cyan/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan">{INTENT_LABEL[t.answer.intent] ?? t.answer.intent}</span>
                        <span className="text-[10px] text-muted" title="Classifier confidence for this intent">{(t.answer.confidence * 100).toFixed(0)}% match</span>
                      </div>
                      <p className="text-sm leading-relaxed text-body">{t.answer.text}</p>
                      {t.answer.figures.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {t.answer.figures.map((f) => (
                            <div key={f.label} className="rounded-lg border border-border-soft bg-panel-light px-2.5 py-1.5">
                              <p className="text-[10px] uppercase tracking-wide text-muted">{f.label}</p>
                              <p className="text-sm font-semibold text-strong">{f.value}</p>
                            </div>
                          ))}
                        </div>
                      )}
                      {t.answer.assumptions.length > 0 && <p className="mt-3 text-[11px] text-amber">{t.answer.assumptions.join(" ")}</p>}
                      {t.answer.intent === "unclear" && t.answer.alternatives.length > 0 && info && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {info.suggestions.slice(0, 4).map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-border-soft px-3 py-1 text-xs text-body hover:border-cyan hover:text-cyan">{s}</button>)}
                        </div>
                      )}
                      {t.answer.links.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-3">
                          {t.answer.links.map((l) => <Link key={l.to} to={l.to} className="text-xs font-medium text-cyan hover:underline">{l.label} →</Link>)}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={endRef} />
      </div>

      <form onSubmit={submit} className="mt-4 flex items-center gap-2 rounded-2xl border border-border-soft bg-white p-2 shadow-sm focus-within:border-cyan focus-within:ring-4 focus-within:ring-cyan/10">
        <input
          value={text} onChange={(e) => setText(e.target.value)} maxLength={400} placeholder="Ask about freight, ports, origins, risk…"
          className="flex-1 bg-transparent px-3 py-2 text-sm text-strong outline-none placeholder:text-slate-400" aria-label="Your question"
        />
        <button type="submit" disabled={busy || text.trim().length < 2} className="flex h-9 w-9 items-center justify-center rounded-xl bg-strong text-on-accent transition hover:bg-cyan disabled:opacity-40" aria-label="Send">
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
