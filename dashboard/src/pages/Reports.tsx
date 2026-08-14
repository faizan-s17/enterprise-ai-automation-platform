import { useState } from "react";
import { roleAtLeast, useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import { useApi } from "../lib/useApi";
import {
  Button,
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  Spinner,
} from "../components/ui";

export default function Reports() {
  const { token, user } = useAuth();
  const canGenerate = roleAtLeast(user?.role, "manager");

  const [kind, setKind] = useState("operations");
  const [days, setDays] = useState(30);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const reports = useApi(() => api.listReports(token!), [token]);

  async function handleGenerate() {
    setGenerating(true);
    setGenError(null);
    try {
      await api.generateReport(token!, kind, days);
      reports.reload();
    } catch (err) {
      setGenError(err instanceof ApiError ? err.message : "Could not generate report.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Business reports & insights"
        subtitle="Metrics collected from the platform, with an AI-written narrative over them."
      />

      {canGenerate && (
        <Card className="mb-6">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-muted">Kind</label>
              <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-44">
                {["operations", "finance", "tickets"].map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-muted">
                Period, days
              </label>
              <Select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="w-32"
              >
                {[7, 14, 30, 60, 90].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </Select>
            </div>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating ? "Generating..." : "Generate"}
            </Button>
          </div>
          {genError && <div className="mt-3"><ErrorNote message={genError} /></div>}
        </Card>
      )}

      {reports.loading && <Spinner label="Loading reports..." />}
      {reports.error && <ErrorNote message={reports.error} />}
      {reports.data && reports.data.length === 0 && (
        <EmptyState message="No reports have been generated yet." />
      )}

      <div className="space-y-4">
        {reports.data?.map((r) => {
          const m = r.metrics as Record<string, number>;
          return (
            <Card key={r.id}>
              <div className="font-semibold text-ink">{r.title}</div>
              <div className="text-xs text-muted">{r.created_at.slice(0, 16).replace("T", " ")}</div>
              <p className="mt-3 whitespace-pre-line text-sm text-slate-700">{r.narrative}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MiniStat label="Documents" value={m.documents_total ?? 0} hint={`${m.document_success_rate ?? 0}% analysed`} />
                <MiniStat label="Tickets" value={m.tickets_total ?? 0} hint={`${m.tickets_open ?? 0} open`} />
                <MiniStat label="Approved value" value={(m.approved_value ?? 0).toLocaleString()} />
                <MiniStat label="Workflow success" value={`${m.workflow_success_rate ?? 0}%`} />
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function MiniStat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg bg-band p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-lg font-bold text-ink">{value}</div>
      {hint && <div className="text-xs text-muted">{hint}</div>}
    </div>
  );
}
