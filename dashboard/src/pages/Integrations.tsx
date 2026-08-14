import { useState } from "react";
import { roleAtLeast, useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Button, Card, ErrorNote, PageHeader, Select, Spinner, TextArea } from "../components/ui";

export default function Integrations() {
  const { token, user } = useAuth();
  const canExecute = roleAtLeast(user?.role, "analyst");
  const integrations = useApi(() => api.listIntegrations(token!), [token]);

  return (
    <div>
      <PageHeader
        title="Connected systems"
        subtitle="CRM, ERP, Google Workspace, and Microsoft 365. Each adapter runs in sandbox until real credentials are set in the environment; supplying them switches it to live with no code change."
      />

      {integrations.loading && <Spinner label="Loading integrations..." />}
      {integrations.error && <ErrorNote message={integrations.error} />}

      <div className="space-y-4">
        {integrations.data?.map((integ) => (
          <IntegrationCard key={integ.kind} integ={integ} canExecute={canExecute} token={token!} />
        ))}
      </div>
    </div>
  );
}

function IntegrationCard({
  integ,
  canExecute,
  token,
}: {
  integ: import("../lib/types").Integration;
  canExecute: boolean;
  token: string;
}) {
  const [op, setOp] = useState(integ.capabilities[0]);
  const [payloadText, setPayloadText] = useState("{}");
  const [result, setResult] = useState<unknown>(null);
  const [health, setHealth] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function checkHealth() {
    setError(null);
    try {
      setHealth(await api.integrationHealth(token, integ.kind));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Health check failed.");
    }
  }

  async function execute() {
    setError(null);
    setResult(null);
    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(payloadText || "{}");
    } catch {
      setError("Payload is not valid JSON.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.executeIntegration(token, integ.kind, op, payload);
      setResult(res.result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Execution failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-ink">{integ.name}</h3>
          <p className="text-xs text-muted">
            Capabilities: {integ.capabilities.join(", ")}
          </p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-xs font-bold capitalize ${
            integ.mode === "live"
              ? "border-emerald-200 bg-emerald-50 text-emerald-600"
              : "border-amber-200 bg-amber-50 text-amber-600"
          }`}
        >
          {integ.mode}
        </span>
      </div>

      <div className="mt-3">
        <Button variant="secondary" onClick={checkHealth}>Check health</Button>
        {health !== null && (
          <pre className="mt-2 overflow-x-auto rounded-lg bg-band p-2 text-xs text-slate-600">
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
      </div>

      {canExecute && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm font-semibold text-slate-600">
            Run an operation
          </summary>
          <div className="mt-3 space-y-2">
            <Select value={op} onChange={(e) => setOp(e.target.value)}>
              {integ.capabilities.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </Select>
            <TextArea
              rows={3}
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              placeholder="Payload (JSON)"
            />
            <Button onClick={execute} disabled={busy}>
              {busy ? "Executing..." : "Execute"}
            </Button>
            {error && <ErrorNote message={error} />}
            {result !== null && (
              <pre className="overflow-x-auto rounded-lg bg-band p-2 text-xs text-slate-600">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </details>
      )}
    </Card>
  );
}
