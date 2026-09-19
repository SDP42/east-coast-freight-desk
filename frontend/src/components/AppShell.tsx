import { Navigate, Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TickerTape from "./TickerTape";
import OceanBackdrop from "./OceanBackdrop";
import { useAuth } from "../lib/auth";

/** Everything under /app requires a signed-in user. */
export default function AppShell() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted">Loading…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="flex min-h-screen text-strong">
      <OceanBackdrop />
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TickerTape />
        <main className="flex-1 overflow-x-hidden p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
