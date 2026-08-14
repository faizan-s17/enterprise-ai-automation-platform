import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, EmptyState, ErrorNote, PageHeader, Select, Spinner, TextInput } from "../components/ui";

export default function AuditLog() {
  const { token } = useAuth();
  const [actionFilter, setActionFilter] = useState("");
  const [limit, setLimit] = useState(100);

  const entries = useApi(() => api.auditLog(token!, { limit }), [token, limit]);

  const filtered = entries.data?.filter((e) =>
    actionFilter ? e.action.toLowerCase().includes(actionFilter.toLowerCase()) : true
  );

  return (
    <div>
      <PageHeader
        title="Audit log"
        subtitle="Every write in the platform, recorded automatically by the API rather than by each page. Admin only."
      />

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <TextInput
          placeholder="Action contains (e.g. approval, document.upload)"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
        />
        <Select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          {[20, 50, 100, 250, 500].map((n) => (
            <option key={n} value={n}>{n} rows</option>
          ))}
        </Select>
      </div>

      {entries.loading && <Spinner label="Loading the audit log..." />}
      {entries.error && <ErrorNote message={entries.error} />}
      {filtered && filtered.length === 0 && <EmptyState message="No audit entries match." />}

      {filtered && filtered.length > 0 && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-band text-xs uppercase text-muted">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Time</th>
                <th className="px-4 py-2.5 font-semibold">Actor</th>
                <th className="px-4 py-2.5 font-semibold">Action</th>
                <th className="px-4 py-2.5 font-semibold">Entity</th>
                <th className="px-4 py-2.5 font-semibold">IP</th>
                <th className="px-4 py-2.5 font-semibold">Detail</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-xs text-muted">
                    {e.created_at.slice(0, 19).replace("T", " ")}
                  </td>
                  <td className="px-4 py-2">{e.actor_email || "system"}</td>
                  <td className="px-4 py-2 font-mono text-xs">{e.action}</td>
                  <td className="px-4 py-2 text-xs text-muted">
                    {e.entity_id ? `${e.entity_type} #${e.entity_id}` : e.entity_type}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted">{e.ip_address || "—"}</td>
                  <td className="max-w-xs truncate px-4 py-2 text-xs text-muted">
                    {JSON.stringify(e.detail)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
