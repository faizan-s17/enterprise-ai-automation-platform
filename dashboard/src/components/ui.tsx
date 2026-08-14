import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

const BADGE_COLORS: Record<string, string> = {
  admin: "text-violet-600 bg-violet-50 border-violet-200",
  manager: "text-blue-600 bg-blue-50 border-blue-200",
  analyst: "text-cyan-600 bg-cyan-50 border-cyan-200",
  viewer: "text-slate-500 bg-slate-50 border-slate-200",

  success: "text-emerald-600 bg-emerald-50 border-emerald-200",
  approved: "text-emerald-600 bg-emerald-50 border-emerald-200",
  analyzed: "text-emerald-600 bg-emerald-50 border-emerald-200",
  resolved: "text-emerald-600 bg-emerald-50 border-emerald-200",
  connected: "text-emerald-600 bg-emerald-50 border-emerald-200",
  live: "text-emerald-600 bg-emerald-50 border-emerald-200",
  closed: "text-slate-500 bg-slate-50 border-slate-200",

  pending: "text-amber-600 bg-amber-50 border-amber-200",
  processing: "text-amber-600 bg-amber-50 border-amber-200",
  open: "text-amber-600 bg-amber-50 border-amber-200",
  in_progress: "text-amber-600 bg-amber-50 border-amber-200",
  sandbox: "text-amber-600 bg-amber-50 border-amber-200",

  rejected: "text-rose-600 bg-rose-50 border-rose-200",
  failed: "text-rose-600 bg-rose-50 border-rose-200",
  error: "text-rose-600 bg-rose-50 border-rose-200",
  urgent: "text-rose-600 bg-rose-50 border-rose-200",

  high: "text-amber-600 bg-amber-50 border-amber-200",
  medium: "text-blue-600 bg-blue-50 border-blue-200",
  low: "text-slate-500 bg-slate-50 border-slate-200",
  cancelled: "text-slate-500 bg-slate-50 border-slate-200",
};

export function Badge({ value }: { value: string }) {
  const key = value.toLowerCase();
  const cls = BADGE_COLORS[key] ?? "text-slate-500 bg-slate-50 border-slate-200";
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${cls}`}
    >
      {key.replace(/_/g, " ")}
    </span>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-border bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${className}`}
    >
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card>
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className="mt-1.5 text-2xl font-bold text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </Card>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...rest
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "danger" | "ghost";
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles: Record<string, string> = {
    primary: "bg-accent text-white hover:bg-accent-dark disabled:bg-slate-300",
    secondary:
      "bg-white text-ink border border-border hover:bg-band disabled:opacity-50",
    danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-slate-300",
    ghost: "text-accent hover:bg-blue-50 disabled:opacity-50",
  };
  return (
    <button
      className={`rounded-lg px-3.5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink placeholder:text-slate-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 ${
        props.className ?? ""
      }`}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink placeholder:text-slate-400 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 ${
        props.className ?? ""
      }`}
    />
  );
}

export function Select({
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 ${
        props.className ?? ""
      }`}
    >
      {children}
    </select>
  );
}

export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-band px-6 py-10 text-center text-sm text-muted">
      {message}
    </div>
  );
}
