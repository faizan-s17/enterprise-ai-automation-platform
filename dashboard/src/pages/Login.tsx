import { type FormEvent, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { Button, TextInput } from "../components/ui";

const DEMO_ACCOUNTS = [
  { role: "Admin", email: "admin@nexgenautomation.com", password: "Admin@12345" },
  { role: "Manager", email: "manager@nexgenautomation.com", password: "Manager@12345" },
  { role: "Analyst", email: "analyst@nexgenautomation.com", password: "Analyst@12345" },
  { role: "Viewer", email: "viewer@nexgenautomation.com", password: "Viewer@12345" },
];

export default function Login() {
  const { token, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<string>("checking");

  useEffect(() => {
    api.health().then((h) => setApiStatus(h.status));
  }, []);

  if (token) return <Navigate to="/" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError("Enter both an email and a password.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Sign in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-band px-4">
      <div className="w-full max-w-sm">
        <div className="mb-7 text-center">
          <div className="text-3xl">🏢</div>
          <h1 className="mt-2 text-xl font-bold text-ink">
            Enterprise AI Automation Platform
          </h1>
          <p className="mt-1 text-sm text-muted">
            NexGen Software House &middot; AI Automation Internship
          </p>
        </div>

        {apiStatus !== "healthy" && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            The API is not reachable. Start it with{" "}
            <code className="rounded bg-amber-100 px-1">
              uvicorn app.main:app --port 8010
            </code>{" "}
            before signing in.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-border bg-white p-6 shadow-sm">
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">Email</label>
            <TextInput
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@nexgenautomation.com"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted">
              Password
            </label>
            <TextInput
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <details className="mt-4 rounded-lg border border-border bg-white p-3 text-xs">
          <summary className="cursor-pointer font-semibold text-slate-600">
            Demo accounts
          </summary>
          <table className="mt-2 w-full text-left">
            <thead className="text-muted">
              <tr>
                <th className="py-1 pr-2">Role</th>
                <th className="py-1 pr-2">Email</th>
                <th className="py-1">Password</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_ACCOUNTS.map((a) => (
                <tr key={a.email} className="border-t border-border">
                  <td className="py-1 pr-2">{a.role}</td>
                  <td className="py-1 pr-2 font-mono">{a.email}</td>
                  <td className="py-1 font-mono">{a.password}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </div>
    </div>
  );
}
