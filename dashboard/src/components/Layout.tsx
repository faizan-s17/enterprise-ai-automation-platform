import { NavLink, Outlet } from "react-router-dom";
import { roleAtLeast, useAuth } from "../context/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  minRole?: string;
}

const NAV: NavItem[] = [
  { to: "/", label: "Overview", icon: "📊" },
  { to: "/documents", label: "Documents", icon: "📄" },
  { to: "/tickets", label: "Tickets", icon: "🎫" },
  { to: "/approvals", label: "Approvals", icon: "✅" },
  { to: "/assistant", label: "AI Assistant", icon: "🤖" },
  { to: "/reports", label: "Reports", icon: "📈" },
  { to: "/workflows", label: "Workflows", icon: "⚙️" },
  { to: "/integrations", label: "Integrations", icon: "🔌" },
  { to: "/users", label: "Users", icon: "👥", minRole: "admin" },
  { to: "/audit-log", label: "Audit Log", icon: "🧾", minRole: "admin" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-band">
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-white">
        <div className="flex items-center gap-2 border-b border-border px-5 py-5">
          <span className="text-xl">🏢</span>
          <div>
            <div className="text-sm font-bold leading-tight text-ink">
              Enterprise Automation
            </div>
            <div className="text-xs text-muted">NexGen Software House</div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV.filter((item) => !item.minRole || roleAtLeast(user?.role, item.minRole)).map(
            (item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-accent"
                      : "text-slate-600 hover:bg-band hover:text-ink"
                  }`
                }
              >
                <span>{item.icon}</span>
                {item.label}
              </NavLink>
            )
          )}
        </nav>

        <div className="border-t border-border p-4">
          <div className="mb-2">
            <div className="text-sm font-semibold text-ink">
              {user?.full_name || user?.email}
            </div>
            <div className="text-xs capitalize text-muted">
              {user?.role} &middot; {user?.department || "—"}
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-band"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto px-8 py-7">
        <Outlet />
      </main>
    </div>
  );
}
