import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Anchor, Check, UserPlus } from "lucide-react";
import OceanBackdrop from "../components/OceanBackdrop";
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
    getPersonas().then(setPersonas).catch(() => setError("Could not load roles — is the backend running?"));
  }, []);

  if (user) return <Navigate to="/app" replace />;

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
    <div className="flex min-h-screen items-center justify-center p-6 text-slate-100">
      <OceanBackdrop />
      <motion.form onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-2xl rounded-2xl border border-border-soft bg-panel/80 p-8 backdrop-blur">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan/20 bg-gradient-to-br from-cyan/20 to-steel/40">
            <Anchor className="h-4 w-4 text-cyan" strokeWidth={1.75} />
          </div>
          <span className="text-sm font-semibold text-white">East Coast Freight Desk</span>
        </Link>

        <h1 className="mt-6 text-2xl font-bold text-white">Create your account</h1>
        <p className="mt-1 text-sm text-muted">Choose the role closest to yours. The desk opens on the tools that role uses most, and you can still use everything.</p>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {personas.map((p) => {
            const v = personaView(p.key);
            const active = role === p.key;
            return (
              <button
                type="button" key={p.key} onClick={() => setRole(p.key)}
                className={`relative rounded-xl border p-4 text-left transition ${active ? "border-cyan/60 bg-cyan/5" : "border-border-soft bg-panel-light/40 hover:border-border-soft hover:bg-panel-light"}`}
              >
                {active && <Check className="absolute right-3 top-3 h-4 w-4 text-cyan" />}
                <v.icon className="h-5 w-5" style={{ color: `rgb(${v.accent})` }} strokeWidth={1.75} />
                <p className="mt-2 text-sm font-semibold text-white">{p.label}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{p.description}</p>
              </button>
            );
          })}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="text-xs text-muted">
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2.5 text-sm text-white outline-none focus:border-cyan/50" />
          </label>
          <label className="text-xs text-muted">
            Email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2.5 text-sm text-white outline-none focus:border-cyan/50" />
          </label>
          <label className="text-xs text-muted sm:col-span-2">
            Password <span className="text-muted/60">(at least 8 characters)</span>
            <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2.5 text-sm text-white outline-none focus:border-cyan/50" />
          </label>
        </div>

        {error && <p className="mt-4 rounded-md border border-down/30 bg-down/10 px-3 py-2 text-xs text-down">{error}</p>}

        <button type="submit" disabled={busy || personas.length === 0} className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-cyan/90 px-4 py-2.5 text-sm font-medium text-navy transition hover:bg-cyan disabled:opacity-50">
          <UserPlus className="h-4 w-4" /> {busy ? "Creating account…" : "Create account"}
        </button>

        <p className="mt-5 text-center text-sm text-muted">
          Already have an account? <Link to="/login" className="text-cyan hover:underline">Sign in</Link>
        </p>
      </motion.form>
    </div>
  );
}
