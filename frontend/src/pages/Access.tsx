import { useCallback, useEffect, useState } from "react";
import { Check, Minus, ShieldCheck } from "lucide-react";
import SpotlightCard from "../components/SpotlightCard";
import { Note, PageHeader, Stat, errText, inputCls } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Matrix { permissions: Record<string, string>; roles: { key: string; label: string; level: number; summary: string; port_scoped: boolean; permissions: string[] }[] }
interface AdminUser { id: number; email: string; full_name: string | null; role: string; role_label: string; assigned_ports: string[]; is_active: boolean; is_demo: boolean }
interface Audit { entries: { id: number; at: string; email: string | null; role: string | null; action: string; detail: string; allowed: boolean }[]; denied_total: number; total: number }

function Level({ n }: { n: number }) {
  return <span className="inline-flex gap-0.5">{[1, 2, 3, 4, 5].map((i) => <span key={i} className={`h-1.5 w-3 rounded-full ${i <= n ? "bg-cyan" : "bg-border-soft"}`} />)}</span>;
}

function AdminPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<{ key: string; label: string }[]>([]);
  const [ports, setPorts] = useState<string[]>([]);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [deniedOnly, setDeniedOnly] = useState(false);
  const [msg, setMsg] = useState("");
  const load = useCallback(async () => {
    const u = (await api.get<{ users: AdminUser[]; roles: { key: string; label: string }[]; ports: string[] }>("/admin/users")).data;
    setUsers(u.users); setRoles(u.roles); setPorts(u.ports);
    setAudit((await api.get<Audit>("/admin/audit", { params: { denied_only: deniedOnly, limit: 60 } })).data);
  }, [deniedOnly]);
  useEffect(() => { load().catch(() => undefined); }, [load]);

  async function patch(id: number, body: object) {
    setMsg("");
    try { await api.patch(`/admin/users/${id}`, body); await load(); setMsg("Saved."); } catch (e) { setMsg(errText(e)); }
  }
  return (
    <>
      <SpotlightCard>
        <div className="p-6">
          <h2 className="text-sm font-semibold text-strong">Users</h2>
          <p className="mt-1 text-xs text-muted">Assign a role to each account. Port officers see only the ports assigned to them. Demo accounts are fixed.</p>
          {msg && <p className="mt-2 text-xs text-body">{msg}</p>}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead><tr className="text-xs text-muted"><th className="py-1">Account</th><th>Role</th><th>Assigned ports</th><th>Active</th></tr></thead>
              <tbody>{users.map((u) => (
                <tr key={u.id} className="border-t border-border-soft align-top">
                  <td className="py-2"><p className="font-medium text-strong">{u.full_name || u.email}{u.is_demo && <span className="ml-2 rounded bg-cyan/10 px-1.5 text-[10px] text-cyan">demo</span>}</p><p className="text-xs text-muted">{u.email}</p></td>
                  <td><select disabled={u.is_demo} value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })} className={inputCls + " !mt-0 w-44"}>{roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}</select></td>
                  <td>{u.role === "port_ops" ? (
                    <div className="flex max-w-xs flex-wrap gap-1">{ports.map((p) => {
                      const on = u.assigned_ports.includes(p);
                      return <button key={p} disabled={u.is_demo} onClick={() => patch(u.id, { assigned_ports: on ? u.assigned_ports.filter((x) => x !== p) : [...u.assigned_ports, p] })}
                        className={`rounded-full border px-2 py-0.5 text-[11px] ${on ? "border-cyan bg-cyan/10 text-cyan" : "border-border-soft text-muted hover:border-cyan"}`}>{p}</button>;
                    })}</div>) : <span className="text-xs text-muted">all ports</span>}</td>
                  <td><input type="checkbox" disabled={u.is_demo} checked={u.is_active} onChange={(e) => patch(u.id, { is_active: e.target.checked })} className="accent-cyan" /></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </SpotlightCard>

      <SpotlightCard>
        <div className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-strong">Audit log</h2>
            <label className="flex items-center gap-2 text-xs text-body"><input type="checkbox" className="accent-cyan" checked={deniedOnly} onChange={(e) => setDeniedOnly(e.target.checked)} /> Denied only</label>
          </div>
          {audit && <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3"><Stat label="Events logged" value={audit.total.toLocaleString()} /><Stat label="Denied requests" value={audit.denied_total} tone={audit.denied_total ? "warn" : "up"} /></div>}
          <div className="mt-3 max-h-80 overflow-y-auto rounded-xl border border-border-soft">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-white"><tr className="text-muted"><th className="px-3 py-2">When</th><th>Who</th><th>Action</th><th>Detail</th></tr></thead>
              <tbody>{audit?.entries.map((e) => (
                <tr key={e.id} className="border-t border-border-soft"><td className="whitespace-nowrap px-3 py-1.5 text-muted">{e.at.slice(5, 16)}</td><td className="text-strong">{e.email ?? "?"}<span className="text-muted"> · {e.role}</span></td>
                  <td>{e.allowed ? e.action : <span className="rounded bg-down/10 px-1.5 text-down">denied</span>}</td><td className="max-w-md truncate text-body" title={e.detail}>{e.detail}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </SpotlightCard>
    </>
  );
}

export default function Access() {
  const { user, can } = useAuth();
  const [m, setM] = useState<Matrix | null>(null);
  useEffect(() => { api.get<Matrix>("/access/matrix").then((r) => setM(r.data)); }, []);
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader title="Access & audit" subtitle="What each role can see, what yours is, and, for administrators, who holds which role and what has been asked." />
      <SpotlightCard>
        <div className="flex flex-wrap items-center gap-4 p-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan/10"><ShieldCheck className="h-6 w-6 text-cyan" /></div>
          <div className="min-w-0 flex-1">
            <p className="text-lg font-semibold text-strong">{user?.role_label} <span className="ml-2 align-middle"><Level n={user?.level ?? 0} /></span></p>
            <p className="text-sm text-body">{user?.role_summary}</p>
            {user?.port_scope && <p className="mt-1 text-xs text-amber">Your ports: {user.port_scope.join(", ") || "none assigned yet"}. Everything port-specific is filtered to these in the database query itself.</p>}
          </div>
        </div>
      </SpotlightCard>

      {m && (
        <SpotlightCard>
          <div className="p-6">
            <h2 className="text-sm font-semibold text-strong">Role and permission matrix</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead><tr className="text-xs text-muted"><th className="py-2 pr-3">Access</th>{m.roles.map((r) => <th key={r.key} className={`px-2 text-center ${r.key === user?.role ? "text-cyan" : ""}`}>{r.label}</th>)}</tr></thead>
                <tbody>
                  <tr className="border-t border-border-soft"><td className="py-1.5 pr-3 text-xs text-muted">Authority level</td>{m.roles.map((r) => <td key={r.key} className="px-2 text-center"><Level n={r.level} /></td>)}</tr>
                  {Object.entries(m.permissions).map(([perm, label]) => (
                    <tr key={perm} className="border-t border-border-soft">
                      <td className="py-1.5 pr-3 text-xs text-body">{label}</td>
                      {m.roles.map((r) => {
                        const on = r.permissions.includes(perm);
                        return <td key={r.key} className={`px-2 text-center ${r.key === user?.role ? "bg-cyan/5" : ""}`}>{on ? <Check className="mx-auto h-4 w-4 text-up" /> : <Minus className="mx-auto h-4 w-4 text-border-soft" />}{on && r.port_scoped && perm.startsWith("ports") ? <span className="block text-[9px] text-amber">assigned only</span> : null}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4"><Note>Access is enforced in the API and in the database queries, not only in this interface. The Ask desk applies the same rules: it refuses questions your role cannot see and records every request in the audit log.</Note></div>
          </div>
        </SpotlightCard>
      )}
      {can("admin:users") && <AdminPanel />}
    </div>
  );
}
