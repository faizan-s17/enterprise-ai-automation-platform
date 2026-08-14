import { useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, EmptyState, ErrorNote, PageHeader, Spinner, StatCard } from "../components/ui";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function Overview() {
  const { token, user } = useAuth();
  const stats = useApi(() => api.dashboardStats(token!), [token]);
  const trend = useApi(() => api.activity(token!, 14), [token]);

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.full_name?.split(" ")[0] || "there"}`}
        subtitle="Live counters pulled from the platform API. Use the sidebar to manage documents, tickets, approvals, and more."
      />

      {stats.loading && <Spinner label="Loading statistics..." />}
      {stats.error && <ErrorNote message={stats.error} />}
      {stats.data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Active users" value={stats.data.users} />
            <StatCard
              label="Documents"
              value={stats.data.documents}
              hint={`${stats.data.documents_analyzed} analysed`}
            />
            <StatCard
              label="Open tickets"
              value={stats.data.tickets_open}
              hint={`of ${stats.data.tickets_total} total`}
            />
            <StatCard label="Pending approvals" value={stats.data.approvals_pending} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Workflow runs today" value={stats.data.workflow_runs_today} />
            <StatCard
              label="Workflow success"
              value={`${stats.data.workflow_success_rate}%`}
            />
            <StatCard
              label="Integrations live"
              value={`${stats.data.integrations_connected} / 4`}
            />
            <StatCard
              label="AI provider"
              value={stats.data.ai_enabled ? "Configured" : "Local fallback"}
            />
          </div>
        </>
      )}

      <div className="mt-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Activity, last 14 days
        </h2>
        <Card>
          {trend.loading && <Spinner label="Loading activity..." />}
          {trend.error && <ErrorNote message={trend.error} />}
          {trend.data && trend.data.length === 0 && (
            <EmptyState message="No activity recorded yet." />
          )}
          {trend.data && trend.data.length > 0 && (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={trend.data}>
                <defs>
                  <linearGradient id="docs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="tickets" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0891b2" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#0891b2" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="runs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis tick={{ fontSize: 11, fill: "#64748B" }} allowDecimals={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="documents" name="Documents" stroke="#2563eb" fill="url(#docs)" strokeWidth={2} />
                <Area type="monotone" dataKey="tickets" name="Tickets" stroke="#0891b2" fill="url(#tickets)" strokeWidth={2} />
                <Area type="monotone" dataKey="workflow_runs" name="Workflow runs" stroke="#059669" fill="url(#runs)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  );
}
