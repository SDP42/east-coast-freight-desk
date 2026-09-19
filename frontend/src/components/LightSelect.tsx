import GlideSelectRaw from "./rb/GlideSelect";

const GlideSelect = GlideSelectRaw as unknown as React.ComponentType<Record<string, unknown>>;

interface Option { value: string; label: string; tag?: string }

/** React Bits GlideSelect in this app's light palette. */
export default function LightSelect({ label, value, options, onChange, width = 190 }: { label?: string; value: string; options: (string | Option)[]; onChange: (v: string) => void; width?: number }) {
  return (
    <div className="gs-light block text-xs font-medium text-body">
      {label && <span className="mb-1 block">{label}</span>}
      <GlideSelect
        options={options} value={value} onChange={(v: string) => onChange(v)} ariaLabel={label ?? "Select"} menuWidth={width} size="md" radius={12}
        surfaceColor="#ffffff" highlightColor="#e3eef7" textColor="#0b2545" accentColor="#0e7490"
      />
    </div>
  );
}
