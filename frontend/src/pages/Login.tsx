import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, LogIn } from "lucide-react";
import AuthShell from "../components/AuthShell";
import PasswordField, { inputClass } from "../components/PasswordField";
import { authErrorMessage, useAuth } from "../lib/auth";

export default function Login() {
  const { user, login, sessionExpired } = useAuth();
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

        <p className="mt-6 text-center text-sm text-muted">
          New here? <Link to="/register" className="font-medium text-cyan hover:underline">Create an account</Link>
        </p>
      </motion.form>
    </AuthShell>
  );
}
