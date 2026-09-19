import type { ReactNode } from "react";
import { AlertTriangle, Info } from "lucide-react";

export const inputCls = "mt-1 w-full rounded-lg border border-border-soft bg-white px-2.5 py-2 text-sm text-strong outline-none transition focus:border-cyan focus:ring-4 focus:ring-cyan/10";
export const btnCls = "rounded-lg bg-strong px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50";

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-strong">{title}</h1>
      {subtitle && <p className="mt-1 max-w-3xl text-sm text-muted">{subtitle}</p>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { key: T; label: string }[]; value: T; onChange: (k: T) => void }) {
  return (
    <div className="mb-5 flex flex-wrap gap-1 rounded-xl border border-border-soft bg-white/70 p-1 backdrop-blur">
      {tabs.map((t) => (
        <button key={t.key} onClick={() => onChange(t.key)} className={`rounded-lg px-3.5 py-1.5 text-sm transition ${value === t.key ? "bg-strong text-on-accent shadow" : "text-body hover:bg-panel-light"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-xs font-medium text-body">{label}{children}</label>;
}

export function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: "up" | "down" | "warn" }) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : tone === "warn" ? "text-amber" : "text-strong";
  return (
    <div className="rounded-xl border border-border-soft bg-panel-light px-3 py-2.5">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold ${color}`}>{value}</p>
    </div>
  );
}

export function Note({ children, kind = "info" }: { children: ReactNode; kind?: "info" | "warn" }) {
  const warn = kind === "warn";
  return (
    <p className={`flex items-start gap-2 rounded-xl border px-3 py-2 text-xs leading-relaxed ${warn ? "border-amber/30 bg-amber/10 text-amber" : "border-border-soft bg-white/70 text-body"}`}>
      {warn ? <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan" />}
      <span>{children}</span>
    </p>
  );
}

export function errText(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return String((d[0] as { msg?: string })?.msg ?? "Invalid input");
  return "Request failed. Is the backend running?";
}

export const tone = (label: string) => (/low|open|stable|A|B/.test(label) ? "up" : /high|tight|drift|D|E|severe/i.test(label) ? "down" : "warn") as "up" | "down" | "warn";

/** Long explanatory text, collapsed by default so pages stay clean. */
export function Fine({ children, title = "How this is calculated" }: { children: ReactNode; title?: string }) {
  return (
    <details className="mt-3 text-xs text-muted">
      <summary className="cursor-pointer select-none hover:text-body">{title}</summary>
      <div className="mt-1.5 leading-relaxed">{children}</div>
    </details>
  );
}
