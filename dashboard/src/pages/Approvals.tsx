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
  TextArea,
  TextInput,
} from "../components/ui";

const ADMIN_THRESHOLD = 500_000;

export default function Approvals() {
  const { token, user } = useAuth();
  const canRequest = roleAtLeast(user?.role, "analyst");
  const canDecide = roleAtLeast(user?.role, "manager");

  const [statusFilter, setStatusFilter] = useState("pending");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("PKR");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<number, string>>({});

  const approvals = useApi(
    () => api.listApprovals(token!, { status: statusFilter || undefined }),
    [token, statusFilter]
  );

  async function handleCreate() {
    if (!title.trim()) {
      setFormError("Title is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createApproval(token!, {
        title,
        description,
        amount: amount ? Number(amount) : null,
        currency,
      });
      setTitle("");
      setDescription("");
      setAmount("");
      setShowForm(false);
      approvals.reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not submit request.");
    } finally {
      setSubmitting(false);
    }
  }

  async function decide(id: number, approved: boolean) {
    try {
      await api.decideApproval(token!, id, approved, notes[id] ?? "");
      approvals.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Decision failed.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Approval workflows"
        subtitle="Requests above PKR 500,000 need an admin; smaller requests need a manager. Nobody may approve their own request."
        action={
          canRequest && (
            <Button onClick={() => setShowForm((v) => !v)}>
              {showForm ? "Cancel" : "New request"}
            </Button>
          )
        }
      />

      {showForm && (
        <Card className="mb-6 space-y-3">
          <TextInput placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextArea
            placeholder="Description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <TextInput
              type="number"
              placeholder="Amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <Select value={currency} onChange={(e) => setCurrency(e.target.value)}>
              {["PKR", "USD", "EUR", "GBP"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </Select>
          </div>
          {formError && <ErrorNote message={formError} />}
          <Button onClick={handleCreate} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit for approval"}
          </Button>
        </Card>
      )}

      <div className="mb-4 w-56">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {["pending", "approved", "rejected", "cancelled", ""].map((s) => (
            <option key={s} value={s}>{s || "All statuses"}</option>
          ))}
        </Select>
      </div>

      {approvals.loading && <Spinner label="Loading approvals..." />}
      {approvals.error && <ErrorNote message={approvals.error} />}
      {approvals.data && approvals.data.length === 0 && (
        <EmptyState message="Nothing to show for this filter." />
      )}

      <div className="space-y-3">
        {approvals.data?.map((a) => {
          const sameUser = a.requested_by_id === user?.id;
          return (
            <Card key={a.id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-ink">{a.title}</div>
                  {a.description && (
                    <div className="text-sm text-muted">{a.description}</div>
                  )}
                </div>
                <div className="text-right">
                  {a.amount !== null && (
                    <>
                      <div className="font-semibold text-ink">
                        {a.amount.toLocaleString()} {a.currency}
                      </div>
                      {a.amount >= ADMIN_THRESHOLD && (
                        <div className="text-xs text-muted">Requires admin</div>
                      )}
                    </>
                  )}
                  <div className="mt-1"><Badge value={a.status} /></div>
                </div>
              </div>

              {a.decision_note && (
                <p className="mt-2 text-xs text-muted">Decision note: {a.decision_note}</p>
              )}

              {canDecide && a.status === "pending" && (
                <div className="mt-3">
                  {sameUser ? (
                    <p className="text-xs text-muted">
                      You raised this request, so you cannot decide on it.
                    </p>
                  ) : (
                    <div className="flex items-center gap-2">
                      <TextInput
                        placeholder="Decision note (optional)"
                        className="flex-1"
                        value={notes[a.id] ?? ""}
                        onChange={(e) =>
                          setNotes((prev) => ({ ...prev, [a.id]: e.target.value }))
                        }
                      />
                      <Button onClick={() => decide(a.id, true)}>Approve</Button>
                      <Button variant="danger" onClick={() => decide(a.id, false)}>
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
