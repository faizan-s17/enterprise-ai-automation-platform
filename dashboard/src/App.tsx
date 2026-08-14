import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { RequireAuth, RequireRole } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Documents from "./pages/Documents";
import Tickets from "./pages/Tickets";
import Approvals from "./pages/Approvals";
import Assistant from "./pages/Assistant";
import Reports from "./pages/Reports";
import Workflows from "./pages/Workflows";
import Integrations from "./pages/Integrations";
import Users from "./pages/Users";
import AuditLog from "./pages/AuditLog";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Overview />} />
          <Route path="documents" element={<Documents />} />
          <Route path="tickets" element={<Tickets />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="reports" element={<Reports />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="integrations" element={<Integrations />} />
          <Route
            path="users"
            element={
              <RequireRole minimum="admin">
                <Users />
              </RequireRole>
            }
          />
          <Route
            path="audit-log"
            element={
              <RequireRole minimum="admin">
                <AuditLog />
              </RequireRole>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
