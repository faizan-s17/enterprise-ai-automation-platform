import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import * as api from "../lib/api";
import type { User } from "../lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const STORAGE_KEY = "platform_access_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY)
  );
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const profile = await api.me(token);
        if (!cancelled) setUser(profile);
      } catch {
        // Token expired or invalid: drop it and fall back to the login screen
        // rather than leaving the app stuck on a spinner.
        if (!cancelled) {
          localStorage.removeItem(STORAGE_KEY);
          setToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadProfile();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function login(email: string, password: string) {
    setError(null);
    try {
      const tokens = await api.login(email, password);
      localStorage.setItem(STORAGE_KEY, tokens.access_token);
      setToken(tokens.access_token);
      const profile = await api.me(tokens.access_token);
      setUser(profile);
    } catch (err) {
      const message = err instanceof api.ApiError ? err.message : "Sign in failed.";
      setError(message);
      throw err;
    }
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

const ROLE_RANK: Record<string, number> = { viewer: 0, analyst: 1, manager: 2, admin: 3 };

export function roleAtLeast(role: string | undefined, minimum: string): boolean {
  return (ROLE_RANK[role ?? "viewer"] ?? 0) >= (ROLE_RANK[minimum] ?? 0);
}
