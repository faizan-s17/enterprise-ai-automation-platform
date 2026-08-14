import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { roleAtLeast, useAuth } from "../context/AuthContext";
import { Spinner } from "./ui";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Loading your session..." />
      </div>
    );
  }
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RequireRole({
  minimum,
  children,
}: {
  minimum: string;
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!roleAtLeast(user?.role, minimum)) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
        This page requires the <strong className="capitalize">{minimum}</strong> role
        or higher. Your role is <strong className="capitalize">{user?.role}</strong>.
      </div>
    );
  }
  return <>{children}</>;
}
