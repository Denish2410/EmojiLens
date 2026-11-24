import clsx from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={clsx("rounded-xl border border-line bg-surface", className)}>
      {children}
    </section>
  );
}

export function CardHeader({ title, actions }: { title: ReactNode; actions?: ReactNode }) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <h2 className="text-sm font-medium">{title}</h2>
      {actions}
    </header>
  );
}

type Variant = "primary" | "ghost";

export function Button({
  variant = "ghost",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...props}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary"
          ? "bg-violet-600 text-white hover:bg-violet-500"
          : "border border-line text-fg hover:bg-surface-2",
        className,
      )}
    />
  );
}

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: "neutral" | "cyan" | "violet" | "amber" | "emerald" | "red";
  children: ReactNode;
  title?: string;
}) {
  const tones = {
    neutral: "border-line text-muted",
    cyan: "border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-300",
    violet: "border-violet-500/30 bg-violet-500/10 text-violet-600 dark:text-violet-300",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    red: "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-300",
  };
  return (
    <span
      title={title}
      className={clsx(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[11px] leading-none",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded bg-surface-2", className)} />;
}
