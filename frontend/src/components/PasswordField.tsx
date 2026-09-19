import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export function passwordStrength(pw: string): { score: number; label: string; tips: string[] } {
  const tips: string[] = [];
  if (pw.length < 8) tips.push("at least 8 characters");
  if (!/[A-Za-z]/.test(pw)) tips.push("a letter");
  if (!/\d/.test(pw)) tips.push("a number");
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Za-z]/.test(pw) && /\d/.test(pw)) score++;
  if (pw.length >= 12) score++;
  if (/[^A-Za-z0-9]/.test(pw) && /[A-Z]/.test(pw)) score++;
  return { score, label: ["Too short", "Weak", "Fair", "Good", "Strong"][score], tips };
}

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  showStrength?: boolean;
  hint?: string;
}

export const inputClass = "mt-1 w-full rounded-xl border border-border-soft bg-white px-3.5 py-2.5 text-sm text-strong outline-none transition placeholder:text-slate-400 focus:border-cyan focus:ring-4 focus:ring-cyan/10";

export default function PasswordField({ label, value, onChange, autoComplete, showStrength = false, hint }: Props) {
  const [show, setShow] = useState(false);
  const st = passwordStrength(value);
  const colors = ["bg-down", "bg-down", "bg-amber", "bg-up", "bg-up"];
  return (
    <label className="block text-xs font-medium text-body">
      {label} {hint && <span className="font-normal text-muted">{hint}</span>}
      <div className="relative">
        <input
          type={show ? "text" : "password"} required value={value} onChange={(e) => onChange(e.target.value)} autoComplete={autoComplete}
          className={`${inputClass} pr-10`}
        />
        <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} className="absolute right-3 top-1/2 mt-0.5 -translate-y-1/2 text-muted hover:text-strong">
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {showStrength && value && (
        <div className="mt-2">
          <div className="flex gap-1">
            {[0, 1, 2, 3].map((i) => <div key={i} className={`h-1 flex-1 rounded-full ${i < st.score ? colors[st.score] : "bg-border-soft"}`} />)}
          </div>
          <p className="mt-1 text-[11px] text-muted">{st.label}{st.tips.length ? ` · needs ${st.tips.join(", ")}` : ""}</p>
        </div>
      )}
    </label>
  );
}
