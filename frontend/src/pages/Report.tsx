import { useEffect, useState } from "react";
import { Printer } from "lucide-react";
import { Note, PageHeader, btnCls } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ROUTE_PERMISSION } from "../lib/personas";

interface Section { title: string; text: string; figures: { label: string; value: string }[] }
interface Briefing { sections: Section[]; scope: string; note: string }

/** A print-ready board pack: the briefing the user's role may see, their access statement, and data caveats. Use the browser's Save as PDF. */
export default function Report() {
  const { user, can } = useAuth();
  const [b, setB] = useState<Briefing | null>(null);
  useEffect(() => { api.get<Briefing>("/briefing").then((r) => setB(r.data)); }, []);
  const tools = Object.entries(ROUTE_PERMISSION).filter(([, need]) => (Array.isArray(need) ? need.some(can) : can(need))).length;
  return (
    <div className="mx-auto max-w-3xl">
      <div className="no-print"><PageHeader title="Board pack" subtitle="A one-page briefing built from the live engines and limited to what your role may see. Print it or save it as a PDF." /></div>
      <button onClick={() => window.print()} className={btnCls + " no-print mb-6 flex items-center gap-2"}><Printer className="h-4 w-4" /> Print or save as PDF</button>

      <article className="rounded-3xl border border-border-soft bg-white p-8 shadow-sm print:border-0 print:p-0 print:shadow-none">
        <header className="border-b border-border-soft pb-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-cyan">East Coast Freight Desk · Smart India Hackathon 2026</p>
          <h1 className="mt-1 text-2xl font-bold text-strong">Coking-coal freight briefing</h1>
          <p className="mt-1 text-xs text-muted">Prepared for {user?.full_name || user?.email} · {user?.role_label} (level {user?.level} of 5) · {new Date().toLocaleDateString(undefined, { dateStyle: "long" })}</p>
          <p className="mt-1 text-xs text-muted">Scope: {b?.scope ?? "…"}. {tools} tool areas are open to this role.</p>
        </header>
        {!b && <p className="mt-6 text-sm text-muted">Building the briefing…</p>}
        {b?.sections.map((s) => (
          <section key={s.title} className="mt-6 break-inside-avoid">
            <h2 className="text-[11px] font-semibold uppercase tracking-widest text-cyan">{s.title}</h2>
            <p className="mt-1 text-sm leading-relaxed text-body">{s.text}</p>
            {s.figures.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{s.figures.map((f) => <span key={f.label} className="rounded-lg border border-border-soft px-2.5 py-1 text-xs text-body">{f.label}: <b className="text-strong">{f.value}</b></span>)}</div>}
          </section>
        ))}
        <footer className="mt-8 border-t border-border-soft pt-4 text-[11px] leading-relaxed text-muted">
          Data notes: the Baltic freight indices end in July 2019 (the current feed is a paid subscription), so market figures illustrate the method rather than today's market. Cost figures are illustrative
          estimates, not quotes. Port congestion combines official Ministry of Ports turnaround with IMF PortWatch call counts. Generated {new Date().toLocaleTimeString()} from the live engines. {b?.note}
        </footer>
      </article>
      <div className="no-print mt-4"><Note>The board pack only contains sections your role may see; another role's pack will differ.</Note></div>
    </div>
  );
}
