import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Anchor, LogIn } from "lucide-react";
import OceanBackdrop from "../components/OceanBackdrop";
import LiveChart from "../components/LiveChart";
import SpotlightCard from "../components/SpotlightCard";
import { authErrorMessage, useAuth } from "../lib/auth";

export default function Login() {
  const { user, login } = useAuth();
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
    <div className="grid min-h-screen text-slate-100 lg:grid-cols-2">
      <OceanBackdrop />

      <div className="hidden flex-col justify-between p-10 lg:flex">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan/20 bg-gradient-to-br from-cyan/20 to-steel/40">
            <Anchor className="h-5 w-5 text-cyan" strokeWidth={1.75} />
          </div>
          <span className="text-sm font-semibold text-white">East Coast Freight Desk</span>
        </Link>
        <div>
          <h2 className="text-3xl font-bold leading-tight text-white">The market moves every day. Your decisions should move first.</h2>
          <p className="mt-3 max-w-md text-sm text-muted">Forecasts, berth fit and cost comparison for India's East Coast coal imports.</p>
          <SpotlightCard className="mt-8 max-w-md">
            <div className="p-4">
              <LiveChart indexName="BDI" label="Baltic Dry Index" height={150} compact />
            </div>
          </SpotlightCard>
        </div>
        <p className="text-xs text-muted">Smart India Hackathon 2026</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <motion.form onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-white">Sign in</h1>
          <p className="mt-1 text-sm text-muted">Welcome back to the desk.</p>

          <label className="mt-6 block text-xs text-muted">
            Email
            <input
              type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2.5 text-sm text-white outline-none focus:border-cyan/50"
            />
          </label>
          <label className="mt-4 block text-xs text-muted">
            Password
            <input
              type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-border-soft bg-panel-light px-3 py-2.5 text-sm text-white outline-none focus:border-cyan/50"
            />
          </label>

          {error && <p className="mt-4 rounded-md border border-down/30 bg-down/10 px-3 py-2 text-xs text-down">{error}</p>}

          <button type="submit" disabled={busy} className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-cyan/90 px-4 py-2.5 text-sm font-medium text-navy transition hover:bg-cyan disabled:opacity-50">
            <LogIn className="h-4 w-4" /> {busy ? "Signing in…" : "Sign in"}
          </button>

          <p className="mt-6 text-center text-sm text-muted">
            New here? <Link to="/register" className="text-cyan hover:underline">Create an account</Link>
          </p>
        </motion.form>
      </div>
    </div>
  );
}
