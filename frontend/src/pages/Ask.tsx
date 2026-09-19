import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { NAV_GROUPS } from "../lib/nav";
import { routeAllowed } from "../lib/personas";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, Bot, Lock, Mic, MicOff, Sparkles, User as UserIcon, Volume2, VolumeX } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { askDesk, getAssistantInfo, type AskAnswer, type AssistantInfo } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Turn { id: number; question: string; answer?: AskAnswer; error?: string }

const INTENT_LABEL: Record<string, string> = {
  ledger: "Fixture ledger", alerts_mine: "Your alerts", my_access: "Your access", users_admin: "Users & audit",
  market_now: "Market snapshot", forecast: "Forecast", recommend_origin: "Origin comparison", port_fit: "Berth fit", risk: "Route risk",
  congestion: "Port congestion", haldia: "Haldia operations", coa_vs_spot: "COA vs spot", demand: "SAIL demand", data_sources: "Data & accuracy", help: "Help", unclear: "Unclear",
};

interface Recognition { start: () => void; stop: () => void; lang: string; interimResults: boolean; continuous: boolean; onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null; onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null }
type RecognitionCtor = new () => Recognition;
const getRecognition = (): RecognitionCtor | null => {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
};
const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

function speak(text: string) {
  if (!canSpeak) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN";
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang === "en-IN") ?? window.speechSynthesis.getVoices().find((v) => v.lang.startsWith("en"));
  if (voice) u.voice = voice;
  u.rate = 1.02;
  window.speechSynthesis.speak(u);
}

export default function Ask() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [listening, setListening] = useState(false);
  const [voiceReply, setVoiceReply] = useState(false);
  const [voiceMsg, setVoiceMsg] = useState("");
  const recRef = useRef<Recognition | null>(null);
  const voiceReplyRef = useRef(false);
  voiceReplyRef.current = voiceReply;
  const speechSupported = getRecognition() !== null;
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<AssistantInfo | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => { getAssistantInfo().then(setInfo).catch(() => setInfo(null)); }, []);
  useEffect(() => { const q = params.get('q'); if (q) { setParams({}, { replace: true }); send(q); } }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns, busy]);

  async function send(question: string) {
    const q = question.trim();
    if (q.length < 2 || busy) return;
    // Voice/text navigation: "open the port map", "go to alerts". Only pages this role may open.
    const m = q.toLowerCase().match(/^(?:please )?(?:open|go to|show me|take me to)(?: the)? (.+?)\??$/);
    if (m) {
      const target = NAV_GROUPS.flatMap((g) => g.links).find((l) => routeAllowed(l.to, can) && (l.label.toLowerCase().includes(m[1]) || m[1].includes(l.label.toLowerCase())));
      if (target) { if (voiceReplyRef.current) speak(`Opening ${target.label}`); navigate(target.to); return; }
    }
    const id = nextId.current++;
    setTurns((t) => [...t, { id, question: q }]);
    setText("");
    setBusy(true);
    try {
      const answer = await askDesk(q);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, answer } : x)));
      if (voiceReplyRef.current) speak(answer.text);
    } catch {
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: "The desk could not answer that just now. Is the backend running?" } : x)));
    } finally {
      setBusy(false);
    }
  }

  const submit = (e: FormEvent) => { e.preventDefault(); send(text); };

  const toggleMic = useCallback(() => {
    const Ctor = getRecognition();
    if (!Ctor) return;
    if (listening) { recRef.current?.stop(); return; }
    const rec = new Ctor();
    rec.lang = "en-IN"; rec.interimResults = true; rec.continuous = false;
    rec.onresult = (e) => {
      const r = e.results[e.results.length - 1];
      const heard = r[0].transcript;
      setText(heard);
      if (r.isFinal) { setVoiceReply(true); send(heard); }
    };
    rec.onerror = (e) => setVoiceMsg(e.error === "not-allowed" ? "Microphone permission was denied." : `Voice input stopped (${e.error}).`);
    rec.onend = () => setListening(false);
    recRef.current = rec; setVoiceMsg(""); setListening(true); rec.start();
  }, [listening]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => { recRef.current?.stop(); if (canSpeak) window.speechSynthesis.cancel(); }, []);
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
              <p className="mt-1 text-xs text-muted">Signed in as <b className="text-body">{user?.role_label}</b>{user?.port_scope ? `, limited to ${user.port_scope.join(", ") || "no ports yet"}` : ""}. I only answer with data your role may see; anything else is politely refused and logged.</p>
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
                        {t.answer.denied ? (
                          <span className="flex items-center gap-1 rounded-full bg-amber/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber"><Lock className="h-3 w-3" /> Outside your access</span>
                        ) : (
                          <span className="rounded-full bg-cyan/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan">{INTENT_LABEL[t.answer.intent] ?? t.answer.intent}</span>
                        )}
                        <span className="text-[10px] text-muted" title="Classifier confidence for this intent">{(t.answer.confidence * 100).toFixed(0)}% match</span>
                        {t.answer.scope && !t.answer.denied && <span className="rounded-full border border-border-soft px-2 py-0.5 text-[10px] text-muted" title="What this answer was limited to">{t.answer.scope}</span>}
                        {canSpeak && <button onClick={() => speak(t.answer!.text)} className="ml-auto text-muted hover:text-cyan" aria-label="Read this answer aloud" title="Read aloud"><Volume2 className="h-3.5 w-3.5" /></button>}
                      </div>
                      <p className={`text-sm leading-relaxed ${t.answer.denied ? "text-amber" : "text-body"}`}>{t.answer.text}</p>
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
        <button type="button" onClick={toggleMic} disabled={!speechSupported} aria-label={listening ? "Stop listening" : "Speak your question"}
          title={speechSupported ? "Speak your question" : "Voice input needs a browser with speech recognition, such as Chrome or Edge"}
          className={`flex h-9 w-9 items-center justify-center rounded-xl transition ${listening ? "animate-pulse bg-down text-white" : "bg-panel-light text-body hover:text-cyan"} disabled:opacity-40`}>
          {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>
        <input
          value={text} onChange={(e) => setText(e.target.value)} maxLength={400} placeholder={listening ? "Listening…" : "Ask about freight, ports, origins, risk…"}
          className="flex-1 bg-transparent px-3 py-2 text-sm text-strong outline-none placeholder:text-slate-400" aria-label="Your question"
        />
        {canSpeak && (
          <button type="button" onClick={() => { if (voiceReply && canSpeak) window.speechSynthesis.cancel(); setVoiceReply(!voiceReply); }} aria-pressed={voiceReply} aria-label="Read answers aloud"
            title={voiceReply ? "Spoken answers on" : "Spoken answers off"} className={`flex h-9 w-9 items-center justify-center rounded-xl transition ${voiceReply ? "bg-cyan/10 text-cyan" : "bg-panel-light text-muted hover:text-cyan"}`}>
            {voiceReply ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
          </button>
        )}
        <button type="submit" disabled={busy || text.trim().length < 2} className="flex h-9 w-9 items-center justify-center rounded-xl bg-strong text-on-accent transition hover:bg-cyan disabled:opacity-40" aria-label="Send">
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
      <p className="mt-2 text-[11px] text-muted">
        {voiceMsg || "Voice: press the microphone and speak; answers are read aloud when the speaker is on. Chrome and Edge send the audio to their own speech service to transcribe it, so avoid confidential details."}
      </p>
    </div>
  );
}
