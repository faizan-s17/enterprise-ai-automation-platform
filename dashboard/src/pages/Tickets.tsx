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

const STATUSES = ["", "open", "in_progress", "resolved", "closed"];
const PRIORITIES = ["", "low", "medium", "high", "urgent"];

export default function Tickets() {
  const { token, user } = useAuth();
  const canWrite = roleAtLeast(user?.role, "analyst");

  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [showForm, setShowForm] = useState(false);

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [requester, setRequester] = useState("");
  const [priority, setPriority] = useState("auto");
  const [category, setCategory] = useState("auto");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const tickets = useApi(
    () =>
      api.listTickets(token!, {
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      }),
    [token, statusFilter, priorityFilter]
  );

  async function handleCreate() {
    if (!subject.trim()) {
      setFormError("Subject is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createTicket(token!, {
        subject,
        description,
        requester_email: requester || null,
        priority: priority === "auto" ? null : priority,
        category: category === "auto" ? null : category,
      });
      setSubject("");
      setDescription("");
      setRequester("");
      setPriority("auto");
      setCategory("auto");
      setShowForm(false);
      tickets.reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  async function setTicketStatus(id: number, next: string) {
    try {
      await api.updateTicket(token!, id, { status: next as never });
      tickets.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Update failed.");
    }
  }

  return (
    <div>
      <PageHeader
        title="Tickets"
        subtitle="Raised manually or automatically from inbound email, with AI priority and category triage."
        action={
          canWrite && (
            <Button onClick={() => setShowForm((v) => !v)}>
              {showForm ? "Cancel" : "New ticket"}
            </Button>
          )
        }
      />

      {showForm && (
        <Card className="mb-6 space-y-3">
          <TextInput
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <TextArea
            placeholder="Description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <TextInput
            placeholder="Requester email (optional)"
            value={requester}
            onChange={(e) => setRequester(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="auto">Auto-triage priority</option>
              {PRIORITIES.filter(Boolean).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </Select>
            <Select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="auto">Auto-triage category</option>
              {["billing", "technical", "contract", "procurement", "hr", "general"].map(
                (c) => (
                  <option key={c} value={c}>{c}</option>
                )
              )}
            </Select>
          </div>
          {formError && <ErrorNote message={formError} />}
          <Button onClick={handleCreate} disabled={submitting}>
            {submitting ? "Creating..." : "Create"}
          </Button>
        </Card>
      )}

      <div className="mb-4 grid grid-cols-2 gap-3 md:w-1/2">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s || "All statuses"}</option>
          ))}
        </Select>
        <Select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>{p || "All priorities"}</option>
          ))}
        </Select>
      </div>

      {tickets.loading && <Spinner label="Loading tickets..." />}
      {tickets.error && <ErrorNote message={tickets.error} />}
      {tickets.data && tickets.data.length === 0 && (
        <EmptyState message="No tickets match the current filters." />
      )}

      <div className="space-y-3">
        {tickets.data?.map((t) => (
          <Card key={t.id}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-semibold text-ink">
                  {t.reference} &middot; {t.subject}
                </div>
                {t.requester_email && (
                  <div className="text-xs text-muted">
                    From {t.requester_email} &middot; source: {t.source}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                <Badge value={t.status} />
                <Badge value={t.priority} />
                <span className="rounded bg-band px-2 py-0.5 text-xs font-mono text-slate-500">
                  {t.category}
                </span>
              </div>
            </div>
            {t.description && (
              <p className="mt-2 text-sm text-slate-700">{t.description.slice(0, 400)}</p>
            )}
            {t.ai_classified && t.ai_reasoning && (
              <p className="mt-2 text-xs italic text-muted">AI triage: {t.ai_reasoning}</p>
            )}
            {canWrite && t.status !== "resolved" && t.status !== "closed" && (
              <div className="mt-3 flex gap-2">
                <Button variant="secondary" onClick={() => setTicketStatus(t.id, "in_progress")}>
                  Start
                </Button>
                <Button variant="secondary" onClick={() => setTicketStatus(t.id, "resolved")}>
                  Resolve
                </Button>
                <Button variant="secondary" onClick={() => setTicketStatus(t.id, "closed")}>
                  Close
                </Button>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
