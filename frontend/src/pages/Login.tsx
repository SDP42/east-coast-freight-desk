import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, LogIn } from "lucide-react";
import AuthShell from "../components/AuthShell";
import PasswordField, { inputClass } from "../components/PasswordField";
import { authErrorMessage, getDemoAccounts, useAuth, type DemoAccount } from "../lib/auth";
import { personaView } from "../lib/personas";

export default function Login() {
  const { user, login, demoLogin, sessionExpired } = useAuth();
  const [demos, setDemos] = useState<DemoAccount[]>([]);
  const [demoBusy, setDemoBusy] = useState<string | null>(null);
  useEffect(() => { getDemoAccounts().then(setDemos).catch(() => setDemos([])); }, []);

  async function tryDemo(email: string) {
    setDemoBusy(email); setError(null);
    try { await demoLogin(email); navigate("/app", { replace: true }); } catch (err) { setError(authErrorMessage(err)); } finally { setDemoBusy(null); }
  }
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/app" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <motion.form onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold text-strong">Welcome back</h1>
        <p className="mt-1 text-sm text-muted">Sign in to the desk.</p>

        {sessionExpired && (
          <p className="mt-5 flex items-start gap-2 rounded-xl border border-amber/30 bg-amber/10 px-3 py-2 text-xs text-amber">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Your session ended. Please sign in again.
          </p>
        )}

        <label className="mt-6 block text-xs font-medium text-body">
          Email
          <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} placeholder="you@company.com" />
        </label>
        <div className="mt-4">
          <PasswordField label="Password" value={password} onChange={setPassword} autoComplete="current-password" />
        </div>

        {error && <p className="mt-4 rounded-xl border border-down/30 bg-down/10 px-3 py-2 text-xs text-down" role="alert">{error}</p>}

        <button type="submit" disabled={busy} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-strong px-4 py-3 text-sm font-medium text-on-accent transition hover:bg-cyan disabled:opacity-50">
          <LogIn className="h-4 w-4" /> {busy ? "Signing in…" : "Sign in"}
        </button>

        {demos.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-widest text-muted"><span className="h-px flex-1 bg-border-soft" />Or try a demo account<span className="h-px flex-1 bg-border-soft" /></div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {demos.map((d) => {
                const v = personaView(d.role);
                return (
                  <button type="button" key={d.email} onClick={() => tryDemo(d.email)} disabled={demoBusy !== null}
                    className="rounded-xl border border-border-soft bg-white p-2.5 text-left transition hover:border-cyan hover:shadow-sm disabled:opacity-50" title={d.summary}>
                    <div className="flex items-center gap-1.5"><v.icon className="h-3.5 w-3.5" style={{ color: `rgb(${v.accent})` }} /><span className="truncate text-xs font-semibold text-strong">{d.role_label}</span></div>
                    <p className="mt-0.5 truncate text-[11px] text-body">{d.full_name}{d.port_scope ? ` · ${d.port_scope.join(", ")}` : ""}</p>
                    <div className="mt-1 flex gap-0.5">{[1, 2, 3, 4, 5].map((n) => <span key={n} className={`h-1 w-3 rounded-full ${n <= d.level ? "bg-cyan" : "bg-border-soft"}`} />)}</div>
                    {demoBusy === d.email && <p className="mt-1 text-[10px] text-cyan">Signing in…</p>}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted">Demo accounts sign in with one click and hold sample data only. Each shows a different level of access.</p>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-muted">
          New here? <Link to="/register" className="font-medium text-cyan hover:underline">Create an account</Link>
        </p>
      </motion.form>
    </AuthShell>
  );
}
