import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import * as api from "../lib/api";
import { ApiError } from "../lib/api";
import { useApi } from "../lib/useApi";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  PageHeader,
  Select,
  Spinner,
  TextInput,
} from "../components/ui";

const ROLES = ["viewer", "analyst", "manager", "admin"];

export default function Users() {
  const { token, user: me } = useAuth();
  const users = useApi(() => api.listUsers(token!), [token]);

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("");
  const [role, setRole] = useState("viewer");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleCreate() {
    if (!email || !password) {
      setFormError("Email and password are required.");
      return;
    }
    if (password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await api.createUser(token!, { email, password, full_name: fullName, department, role });
      setEmail(""); setFullName(""); setDepartment(""); setPassword(""); setRole("viewer");
      setShowForm(false);
      users.reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create user.");
    } finally {
      setSubmitting(false);
    }
  }

  async function changeRole(id: number, newRole: string) {
    try {
      await api.updateUser(token!, id, { role: newRole as never });
      users.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not change role.");
    }
  }

  async function toggleActive(id: number, active: boolean) {
    try {
      await api.updateUser(token!, id, { is_active: !active });
      users.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not update status.");
    }
  }

  return (
    <div>
      <PageHeader
        title="User management"
        subtitle="Create accounts and change roles. Admin only. You cannot change your own role or deactivate yourself, so the platform can never be left with no administrator."
        action={<Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "New user"}</Button>}
      />

      {showForm && (
        <Card className="mb-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <TextInput placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextInput placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <TextInput placeholder="Department" value={department} onChange={(e) => setDepartment(e.target.value)} />
            <Select value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          </div>
          <TextInput
            type="password"
            placeholder="Temporary password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {formError && <ErrorNote message={formError} />}
          <Button onClick={handleCreate} disabled={submitting}>
            {submitting ? "Creating..." : "Create"}
          </Button>
        </Card>
      )}

      {users.loading && <Spinner label="Loading users..." />}
      {users.error && <ErrorNote message={users.error} />}

      <div className="space-y-3">
        {users.data?.map((u) => {
          const isSelf = u.id === me?.id;
          return (
            <Card key={u.id}>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-semibold text-ink">{u.full_name || u.email}</div>
                  <div className="text-xs text-muted">
                    {u.email} &middot; {u.department || "no department"}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge value={u.role} />
                  <span className="text-xs text-muted">
                    {u.is_active ? "🟢 active" : "⚪ disabled"}
                  </span>
                  {isSelf ? (
                    <span className="text-xs text-muted">This is you</span>
                  ) : (
                    <>
                      <Select
                        value={u.role}
                        onChange={(e) => changeRole(u.id, e.target.value)}
                        className="w-32"
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </Select>
                      <Button variant="secondary" onClick={() => toggleActive(u.id, u.is_active)}>
                        {u.is_active ? "Disable" : "Enable"}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
