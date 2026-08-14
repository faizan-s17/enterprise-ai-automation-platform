import { useState } from "react";
import { roleAtLeast, useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import { useApi } from "../lib/useApi";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorNote,
  PageHeader,
  Select,
  Spinner,
} from "../components/ui";

const PRESET_WORKFLOWS = [
  "document-intake",
  "invoice-approval",
  "ticket-triage",
  "crm-sync",
];

export default function Workflows() {
  const { token, user } = useAuth();
  const canTrigger = roleAtLeast(user?.role, "analyst");

  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState(PRESET_WORKFLOWS[0]);
  const [triggering, setTriggering] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const runs = useApi(
    () => api.listRuns(token!, { status: statusFilter || undefined }),
    [token, statusFilter]
  );

  async function handleTrigger() {
    setTriggering(true);
    setTriggerMsg(null);
    try {
      const run = await api.triggerWorkflow(token!, selected);
      if (run.status === "success") {
        const note = (run.result as { note?: string })?.note ?? "";
        setTriggerMsg({
          ok: true,
          text: `Run #${run.id} completed in ${run.duration_ms} ms.${note ? " " + note : ""}`,
        });
      } else {
        setTriggerMsg({ ok: false, text: `Run #${run.id} failed: ${run.error}` });
      }
      runs.reload();
    } catch (err) {
      setTriggerMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : "Trigger failed.",
      });
    } finally {
      setTriggering(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Workflow automation"
        subtitle="Runs triggered from this platform, plus n8n workflows that call back with their result."
      />

      {canTrigger && (
        <Card className="mb-6">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-muted">Workflow</label>
              <Select value={selected} onChange={(e) => setSelected(e.target.value)} className="w-56">
                {PRESET_WORKFLOWS.map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </Select>
            </div>
            <Button onClick={handleTrigger} disabled={triggering}>
              {triggering ? "Triggering..." : "Trigger"}
            </Button>
          </div>
          {triggerMsg && (
            <p className={`mt-3 text-sm ${triggerMsg.ok ? "text-emerald-600" : "text-rose-600"}`}>
              {triggerMsg.text}
            </p>
          )}
        </Card>
      )}

      <div className="mb-4 w-56">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {["", "running", "success", "failed"].map((s) => (
            <option key={s} value={s}>{s || "All statuses"}</option>
          ))}
        </Select>
      </div>

      {runs.loading && <Spinner label="Loading workflow runs..." />}
      {runs.error && <ErrorNote message={runs.error} />}
      {runs.data && runs.data.length === 0 && <EmptyState message="No workflow runs match." />}

      <div className="space-y-3">
        {runs.data?.map((r) => (
          <Card key={r.id}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-semibold text-ink">{r.workflow_name}</div>
                <div className="text-xs text-muted">
                  {r.started_at.slice(0, 19).replace("T", " ")} &middot; via {r.trigger_source}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge value={r.status} />
                {r.duration_ms !== null && (
                  <span className="text-xs text-muted">{r.duration_ms} ms</span>
                )}
              </div>
            </div>
            {r.error && <div className="mt-2"><ErrorNote message={r.error} /></div>}
            {!r.error && Object.keys(r.result).length > 0 && (
              <pre className="mt-2 overflow-x-auto rounded-lg bg-band p-2 text-xs text-slate-600">
                {JSON.stringify(r.result, null, 2)}
              </pre>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
