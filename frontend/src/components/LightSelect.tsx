interface Option { value: string; label: string; tag?: string }

/** Native select in this app's light palette; always opens, never clipped by a parent card. */
export default function LightSelect({ label, value, options, onChange, width = 190 }: { label?: string; value: string; options: (string | Option)[]; onChange: (v: string) => void; width?: number }) {
  const opts = options.map((o) => (typeof o === "string" ? { value: o, label: o } : o));
  return (
    <label className="block text-xs font-medium text-body">
      {label && <span className="mb-1 block">{label}</span>}
      <select
        value={value} onChange={(e) => onChange(e.target.value)} aria-label={label ?? "Select"} style={{ minWidth: width }}
        className="w-full rounded-xl border border-border-soft bg-white px-3 py-2 text-sm text-strong shadow-sm focus:border-cyan focus:outline-none"
      >
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
