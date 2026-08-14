export type Role = "viewer" | "analyst" | "manager" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  department: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_minutes: number;
}

export type DocType =
  | "invoice"
  | "contract"
  | "purchase_order"
  | "receipt"
  | "report"
  | "other";
export type DocStatus = "uploaded" | "processing" | "analyzed" | "failed";

export interface Document {
  id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  doc_type: DocType;
  status: DocStatus;
  ai_summary: string;
  ai_fields: Record<string, unknown>;
  error: string;
  uploaded_by_id: number | null;
  created_at: string;
  processed_at: string | null;
  extracted_text?: string;
}

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketSource = "email" | "api" | "manual" | "document";

export interface Ticket {
  id: number;
  reference: string;
  subject: string;
  description: string;
  source: TicketSource;
  status: TicketStatus;
  priority: TicketPriority;
  category: string;
  ai_classified: boolean;
  ai_reasoning: string;
  requester_email: string;
  assigned_to_id: number | null;
  document_id: number | null;
  created_at: string;
  resolved_at: string | null;
}

export type ApprovalStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface Approval {
  id: number;
  title: string;
  description: string;
  entity_type: string;
  entity_id: number | null;
  amount: number | null;
  currency: string;
  status: ApprovalStatus;
  decision_note: string;
  requested_by_id: number | null;
  approver_id: number | null;
  decided_by_id: number | null;
  created_at: string;
  decided_at: string | null;
}

export interface AssistantAnswer {
  question: string;
  answer: string;
  sources: { type: string; id: number; label: string; [k: string]: unknown }[];
  model: string;
  grounded: boolean;
}

export interface Report {
  id: number;
  title: string;
  kind: string;
  period_start: string | null;
  period_end: string | null;
  metrics: Record<string, unknown>;
  narrative: string;
  created_at: string;
}

export type RunStatus = "running" | "success" | "failed";

export interface WorkflowRun {
  id: number;
  workflow_name: string;
  trigger_source: string;
  status: RunStatus;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
}

export interface Integration {
  name: string;
  kind: string;
  status: string;
  mode: "live" | "sandbox";
  capabilities: string[];
}

export interface DashboardStats {
  users: number;
  documents: number;
  documents_analyzed: number;
  tickets_open: number;
  tickets_total: number;
  approvals_pending: number;
  workflow_runs_today: number;
  workflow_success_rate: number;
  integrations_connected: number;
  ai_enabled: boolean;
}

export interface ActivityDay {
  date: string;
  documents: number;
  tickets: number;
  workflow_runs: number;
}

export interface AuditEntry {
  id: number;
  action: string;
  actor_id: number | null;
  actor_email: string | null;
  entity_type: string;
  entity_id: number | null;
  detail: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}
