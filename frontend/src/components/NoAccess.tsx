import { Link } from "react-router-dom";
import { Lock } from "lucide-react";
import { useAuth } from "../lib/auth";

/** Shown in place of a page the user's role may not open. */
export default function NoAccess() {
  const { user } = useAuth();
  return (
    <div className="mx-auto mt-16 max-w-lg rounded-3xl border border-border-soft bg-white/90 p-8 text-center shadow-sm backdrop-blur">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber/10"><Lock className="h-6 w-6 text-amber" /></div>
      <h1 className="mt-4 text-xl font-bold text-strong">This page is outside your access</h1>
      <p className="mt-2 text-sm text-body">
        You are signed in as <b>{user?.role_label}</b> (level {user?.level} of 5). {user?.role_summary}
      </p>
      <p className="mt-2 text-sm text-muted">Someone with a higher role, such as an administrator, can see this data or change your role.</p>
      <div className="mt-6 flex justify-center gap-3">
        <Link to="/app" className="rounded-xl bg-strong px-4 py-2 text-sm font-medium text-on-accent hover:bg-cyan">Back to overview</Link>
        <Link to="/app/access" className="rounded-xl border border-border-soft px-4 py-2 text-sm text-body hover:border-cyan hover:text-cyan">See what I can access</Link>
      </div>
    </div>
  );
}
