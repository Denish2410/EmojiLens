/** Horizontal bars for a categorical count distribution. Values are shown exactly. */
export function Distribution({
  title,
  data,
  tone = "violet",
}: {
  title: string;
  data: Record<string, number>;
  tone?: "violet" | "cyan";
}) {
  const entries = Object.entries(data);
  const total = entries.reduce((a, [, n]) => a + n, 0);
  const max = Math.max(1, ...entries.map(([, n]) => n));
  return (
    <figure className="min-w-0">
      <figcaption className="mb-2 text-xs font-medium text-muted">{title}</figcaption>
      {entries.length === 0 ? (
        <p className="text-xs text-muted">No data.</p>
      ) : (
        <ul className="flex flex-col gap-1.5" aria-label={title}>
          {entries.map(([k, n]) => (
            <li key={k} className="grid grid-cols-[6.5rem_1fr_4.5rem] items-center gap-2 text-xs">
              <span className="truncate font-mono" title={k}>
                {k}
              </span>
              <span className="h-2 rounded-full bg-surface-2" aria-hidden="true">
                <span
                  className={`block h-2 rounded-full ${tone === "violet" ? "bg-violet-500/70" : "bg-cyan-500/70"}`}
                  style={{ width: `${(n / max) * 100}%` }}
                />
              </span>
              <span className="text-right font-mono tabular-nums">
                {n}
                <span className="text-muted"> ({total ? Math.round((n / total) * 100) : 0}%)</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}
