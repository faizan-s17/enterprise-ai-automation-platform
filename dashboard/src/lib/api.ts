import axios, { type AxiosInstance, isAxiosError } from "axios";
import type {
  Approval,
  AssistantAnswer,
  AuditEntry,
  DashboardStats,
  Document as PlatformDocument,
  Integration,
  Report,
  Ticket,
  Tokens,
  User,
  WorkflowRun,
  ActivityDay,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";
const API_PREFIX = "/api/v1";

/** Thin wrapper so every call surfaces one clean error shape.
 *
 * FastAPI's default error body is `{ detail: string | ValidationError[] }`;
 * flattening that here means every page's catch block gets a plain string,
 * not a shape it has to know about.
 */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function client(token?: string | null): AxiosInstance {
  return axios.create({
    baseURL: `${API_BASE_URL}${API_PREFIX}`,
    timeout: 30_000,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

function detailFrom(data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((e) => {
          const loc = Array.isArray(e?.loc) ? e.loc.slice(1).join(".") : "";
          return loc ? `${loc}: ${e.msg}` : String(e?.msg ?? e);
        })
        .join("; ");
    }
  }
  return "Something went wrong.";
}

async function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  try {
    const res = await promise;
    return res.data;
  } catch (err) {
    if (isAxiosError(err)) {
      if (!err.response) {
        throw new ApiError(
          0,
          `Cannot reach the API at ${API_BASE_URL}. Is the server running?`
        );
      }
      throw new ApiError(err.response.status, detailFrom(err.response.data));
    }
    throw err;
  }
}

// ------------------------------------------------------------------- auth
export function login(email: string, password: string): Promise<Tokens> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  return unwrap(
    axios.post(`${API_BASE_URL}${API_PREFIX}/auth/login`, form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
  );
}

export function me(token: string): Promise<User> {
  return unwrap(client(token).get("/auth/me"));
}

export async function health(): Promise<{ status: string; [k: string]: unknown }> {
  try {
    const res = await axios.get(`${API_BASE_URL}/health`, { timeout: 8000 });
    return res.data;
  } catch {
    return { status: "unreachable" };
  }
}

// -------------------------------------------------------------------- admin
export function dashboardStats(token: string): Promise<DashboardStats> {
  return unwrap(client(token).get("/admin/stats"));
}

export function activity(token: string, days = 14): Promise<ActivityDay[]> {
  return unwrap(client(token).get("/admin/activity", { params: { days } }));
}

export function auditLog(
  token: string,
  params: { limit?: number; action?: string } = {}
): Promise<AuditEntry[]> {
  return unwrap(client(token).get("/admin/audit-log", { params }));
}

// ---------------------------------------------------------------- documents
export function listDocuments(
  token: string,
  params: Record<string, string | undefined> = {}
): Promise<PlatformDocument[]> {
  return unwrap(client(token).get("/documents", { params }));
}

export function uploadDocument(token: string, file: File): Promise<PlatformDocument> {
  const form = new FormData();
  form.append("file", file);
  return unwrap(
    client(token).post("/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  );
}

export function reanalyseDocument(token: string, id: number): Promise<PlatformDocument> {
  return unwrap(client(token).post(`/documents/${id}/reanalyse`));
}

export function deleteDocument(token: string, id: number): Promise<void> {
  return unwrap(client(token).delete(`/documents/${id}`));
}

// ------------------------------------------------------------------ tickets
export function listTickets(
  token: string,
  params: Record<string, string | undefined> = {}
): Promise<Ticket[]> {
  return unwrap(client(token).get("/tickets", { params }));
}

export function createTicket(
  token: string,
  payload: {
    subject: string;
    description?: string;
    requester_email?: string | null;
    priority?: string | null;
    category?: string | null;
  }
): Promise<Ticket> {
  return unwrap(client(token).post("/tickets", payload));
}

export function updateTicket(
  token: string,
  id: number,
  payload: Partial<Pick<Ticket, "status" | "priority" | "category" | "assigned_to_id">>
): Promise<Ticket> {
  return unwrap(client(token).patch(`/tickets/${id}`, payload));
}

// ---------------------------------------------------------------- approvals
export function listApprovals(
  token: string,
  params: Record<string, string | undefined> = {}
): Promise<Approval[]> {
  return unwrap(client(token).get("/approvals", { params }));
}

export function createApproval(
  token: string,
  payload: { title: string; description?: string; amount?: number | null; currency?: string }
): Promise<Approval> {
  return unwrap(client(token).post("/approvals", payload));
}

export function decideApproval(
  token: string,
  id: number,
  approved: boolean,
  note: string
): Promise<Approval> {
  return unwrap(client(token).post(`/approvals/${id}/decision`, { approved, note }));
}

// --------------------------------------------------------------- assistant
export function askAssistant(token: string, question: string): Promise<AssistantAnswer> {
  return unwrap(client(token).post("/assistant/ask", { question }));
}

export function assistantSuggestions(token: string): Promise<string[]> {
  return unwrap(client(token).get("/assistant/suggestions"));
}

// ----------------------------------------------------------------- reports
export function listReports(token: string): Promise<Report[]> {
  return unwrap(client(token).get("/reports", { params: { limit: 20 } }));
}

export function generateReport(
  token: string,
  kind: string,
  days: number
): Promise<Report> {
  return unwrap(client(token).post("/reports/generate", { kind, days }));
}

// --------------------------------------------------------------- workflows
export function listRuns(
  token: string,
  params: Record<string, string | undefined> = {}
): Promise<WorkflowRun[]> {
  return unwrap(client(token).get("/workflows/runs", { params: { ...params, limit: "100" } }));
}

export function triggerWorkflow(
  token: string,
  workflow_name: string
): Promise<WorkflowRun> {
  return unwrap(client(token).post("/workflows/trigger", { workflow_name, payload: {} }));
}

// ----------------------------------------------------------- integrations
export function listIntegrations(token: string): Promise<Integration[]> {
  return unwrap(client(token).get("/integrations"));
}

export function integrationHealth(
  token: string,
  key: string
): Promise<Record<string, unknown>> {
  return unwrap(client(token).get(`/integrations/${key}/health`));
}

export function executeIntegration(
  token: string,
  key: string,
  operation: string,
  payload: Record<string, unknown>
): Promise<{ integration: string; operation: string; result: Record<string, unknown> }> {
  return unwrap(client(token).post(`/integrations/${key}/execute`, { operation, payload }));
}

// ---------------------------------------------------------------------- users
export function listUsers(token: string): Promise<User[]> {
  return unwrap(client(token).get("/users", { params: { limit: 200 } }));
}

export function createUser(
  token: string,
  payload: {
    email: string;
    password: string;
    full_name: string;
    department: string;
    role: string;
  }
): Promise<User> {
  return unwrap(client(token).post("/users", payload));
}

export function updateUser(
  token: string,
  id: number,
  payload: Partial<Pick<User, "role" | "is_active" | "full_name" | "department">>
): Promise<User> {
  return unwrap(client(token).patch(`/users/${id}`, payload));
}
