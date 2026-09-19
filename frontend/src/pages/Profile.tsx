import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2 } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import PasswordField, { inputClass, passwordStrength } from "../components/PasswordField";
import { authErrorMessage, getPersonas, useAuth, type Persona } from "../lib/auth";

function Msg({ m }: { m: { ok: boolean; text: string } | null }) {
  return m ? <p className={`mt-3 flex items-center gap-2 text-xs ${m.ok ? "text-up" : "text-down"}`}>{m.ok && <CheckCircle2 className="h-3.5 w-3.5" />}{m.text}</p> : null;
}

export default function Profile() {
  const { user, updateProfile, changePassword } = useAuth();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [role, setRole] = useState(user?.role ?? "chartering_analyst");
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => { getPersonas().then(setPersonas).catch(() => setPersonas([])); }, []);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    try {
      await updateProfile(fullName, role);
      setProfileMsg({ ok: true, text: "Profile saved." });
    } catch (err) {
      setProfileMsg({ ok: false, text: authErrorMessage(err) });
    }
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    try {
      await changePassword(current, next);
      setCurrent(""); setNext("");
      setPwMsg({ ok: true, text: "Password changed. Use it next time you sign in." });
    } catch (err) {
      setPwMsg({ ok: false, text: authErrorMessage(err) });
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-strong">Your account</h1>
        <p className="mt-1 text-sm text-muted">{user?.email}</p>
      </div>

      <SpotlightCard>
        <form onSubmit={saveProfile} className="p-6">
          <h2 className="text-sm font-semibold text-strong">Profile</h2>
          <label className="mt-4 block text-xs font-medium text-body">
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputClass} />
          </label>
          {user?.role !== "admin" && (
            <label className="mt-4 block text-xs font-medium text-body">
              Role
              <select value={role} onChange={(e) => setRole(e.target.value)} className={inputClass}>
                {personas.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
              </select>
            </label>
          )}
          <button type="submit" className="mt-5 rounded-xl bg-strong px-5 py-2.5 text-sm font-medium text-on-accent hover:bg-cyan">Save profile</button>
          <Msg m={profileMsg} />
        </form>
      </SpotlightCard>

      <SpotlightCard>
        <form onSubmit={savePassword} className="p-6">
          <h2 className="text-sm font-semibold text-strong">Change password</h2>
          <div className="mt-4 space-y-4">
            <PasswordField label="Current password" value={current} onChange={setCurrent} autoComplete="current-password" />
            <PasswordField label="New password" value={next} onChange={setNext} autoComplete="new-password" showStrength />
          </div>
          <button type="submit" disabled={!current || passwordStrength(next).tips.length > 0} className="mt-5 rounded-xl bg-strong px-5 py-2.5 text-sm font-medium text-on-accent hover:bg-cyan disabled:opacity-50">Change password</button>
          <Msg m={pwMsg} />
        </form>
      </SpotlightCard>
    </div>
  );
}
