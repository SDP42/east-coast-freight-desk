import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, UserPlus } from "lucide-react";
import AuthShell from "../components/AuthShell";
import PasswordField, { inputClass, passwordStrength } from "../components/PasswordField";
import { authErrorMessage, getPersonas, useAuth, type Persona } from "../lib/auth";
import { personaView } from "../lib/personas";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [role, setRole] = useState("chartering_analyst");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPersonas().then(setPersonas).catch(() => setError("Could not load roles. Is the backend running?"));
  }, []);

  if (user) return <Navigate to="/app" replace />;

  const strong = passwordStrength(password).tips.length === 0;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(email.trim(), password, fullName.trim(), role);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell wide>
      <motion.form onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold text-strong">Create your account</h1>
        <p className="mt-1 text-sm text-muted">Choose the persona closest to yours: the desk opens on the tools that persona uses most. New accounts start as <b>Viewer</b> (public market data); an administrator then assigns your access role.</p>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {personas.map((p) => {
            const v = personaView(p.key);
            const active = role === p.key;
            return (
              <button
                type="button" key={p.key} onClick={() => setRole(p.key)} aria-pressed={active}
                className={`relative rounded-2xl border p-4 text-left transition ${active ? "border-cyan bg-cyan/5 ring-4 ring-cyan/10" : "border-border-soft bg-white hover:border-cyan/40"}`}
              >
                {active && <Check className="absolute right-3 top-3 h-4 w-4 text-cyan" />}
                <v.icon className="h-5 w-5" style={{ color: `rgb(${v.accent})` }} strokeWidth={1.75} />
                <p className="mt-2 text-sm font-semibold text-strong">{p.label}</p>
                <p className="mt-1 text-xs leading-relaxed text-body">{p.description}</p>
              </button>
            );
          })}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="text-xs font-medium text-body">
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" className={inputClass} />
          </label>
          <label className="text-xs font-medium text-body">
            Email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" className={inputClass} />
          </label>
          <div className="sm:col-span-2">
            <PasswordField label="Password" hint="(8+ characters, with a letter and a number)" value={password} onChange={setPassword} autoComplete="new-password" showStrength />
          </div>
        </div>

        {error && <p className="mt-4 rounded-xl border border-down/30 bg-down/10 px-3 py-2 text-xs text-down" role="alert">{error}</p>}

        <button type="submit" disabled={busy || personas.length === 0 || !strong} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-strong px-4 py-3 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50">
          <UserPlus className="h-4 w-4" /> {busy ? "Creating account…" : "Create account"}
        </button>

        <p className="mt-5 text-center text-sm text-muted">
          Already have an account? <Link to="/login" className="font-medium text-cyan hover:underline">Sign in</Link>
        </p>
      </motion.form>
    </AuthShell>
  );
}
