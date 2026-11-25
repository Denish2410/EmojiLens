import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight, CheckCircle2, CircleAlert, CircleDashed, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { api } from "../api/client";
import type { DashboardSummary } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";

const VARIETIES = ["en", "hi", "gu", "hi-Latn", "gu-Latn"];
const STATUS_ORDER = ["queued", "running", "cancelling", "completed", "failed", "cancelled", "interrupted"];
const nf = new Intl.NumberFormat();

function Stat({ label, value, sub, to }: { label: string; value: number; sub: ReactNode; to: string }) {
  return (
    <Link to={to} className="group flex min-w-0 flex-col gap-1 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-violet-500/50">
      <span className="text-xs text-muted">{label}</span>
      <span className="font-mono text-2xl font-semibold tabular-nums tracking-tight">{nf.format(value)}</span>
      <span className="truncate text-xs text-muted">{sub}</span>
    </Link>
  );
}

function Languages({ counts }: { counts: Record<string, number> }) {
  const keys = [...VARIETIES, ...Object.keys(counts).filter((k) => !VARIETIES.includes(k)).sort()];
  const max = Math.max(1, ...Object.values(counts));
  return (
    <ul className="flex flex-col gap-2" aria-label="Source records by language variety">
      {keys.map((k) => {
        const n = counts[k] ?? 0;
        return (
          <li key={k} className="grid grid-cols-[4.5rem_1fr_3.5rem] items-center gap-3 text-sm" title={`${k}: ${nf.format(n)} source records`}>
            <span className="font-mono text-xs">{k}</span>
            <div className="h-2 rounded-full bg-surface-2">
              {n > 0 && <div className="h-2 rounded-full bg-violet-500" style={{ width: `${Math.max(2, (n / max) * 100)}%` }} />}
            </div>
            <span className={clsx("text-right font-mono text-xs tabular-nums", n === 0 && "text-muted")}>{nf.format(n)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ReadinessList({ items }: { items: DashboardSummary["readiness"] }) {
  return (
    <ul className="flex flex-col divide-y divide-line">
      {items.map((r) => (
        <li key={r.key} className="flex items-start gap-3 px-4 py-2.5" data-testid={`readiness-${r.key}`}>
          {r.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" aria-label="met" /> : <CircleDashed className="mt-0.5 size-4 shrink-0 text-amber-500" aria-label="not met" />}
          <div className="min-w-0">
            <p className="text-sm font-medium">{r.label}</p>
            <p className="text-xs text-muted">{r.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function Pipeline({ d }: { d: DashboardSummary }) {
  const rows: [string, string, string][] = [
    ["Annotation", `${nf.format(d.annotation.annotations)} annotations · ${nf.format(d.annotation.adjudications)} adjudicated`, "/annotation"],
    ["CRSC", `${nf.format(d.crsc.metric_rows)} metric rows from ${nf.format(d.crsc.experiments)} experiment(s)`, "/crsc"],
    ["Multimodal", `${nf.format(d.multimodal.render_artifacts)} rendered artifacts`, "/multimodal"],
    ["EmojiGuard", `${nf.format(d.guard.evaluations)} evaluations · ${nf.format(d.guard.detector_artifacts)} detectors`, "/guard"],
  ];
  return (
    <ul className="flex flex-col divide-y divide-line">
      {rows.map(([name, detail, to]) => (
        <li key={name}>
          <Link to={to} className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-surface-2">
            <span className="min-w-0"><span className="block text-sm font-medium">{name}</span><span className="block truncate text-xs text-muted">{detail}</span></span>
            <ArrowRight className="size-3.5 shrink-0 text-muted" />
          </Link>
        </li>
      ))}
    </ul>
  );
}

function SystemStatus() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 1 });
  const ready = useQuery({ queryKey: ["ready"], queryFn: api.ready, retry: 1 });
  const failed = health.isError || ready.isError;
  return (
    <Card>
      <CardHeader
        title="System status"
        actions={
          <Button onClick={() => { void health.refetch(); void ready.refetch(); }} aria-label="Refresh system status">
            <RefreshCw className="size-3.5" /> Refresh
          </Button>
        }
      />
      <div className="p-4">
        {health.isPending || ready.isPending ? (
          <div className="flex flex-col gap-2" data-testid="status-loading"><Skeleton className="h-5 w-48" /><Skeleton className="h-5 w-64" /></div>
        ) : failed ? (
          <div className="flex items-start gap-2 text-sm text-red-500">
            <CircleAlert className="mt-0.5 size-4 shrink-0" />
            <div><p className="font-medium">API unreachable</p><p className="text-muted">Start the API with <code className="font-mono">scripts/dev-api.sh</code>, then refresh.</p></div>
          </div>
        ) : (
          <ul className="flex flex-col gap-2 text-sm">
            <li className="flex items-center gap-2"><CheckCircle2 className="size-4 shrink-0 text-emerald-500" />API {health.data?.version} is live</li>
            {ready.data?.checks.map((c) => (
              <li key={c.name} className="flex min-w-0 items-center gap-2">
                {c.ok ? <CheckCircle2 className="size-4 shrink-0 text-emerald-500" /> : <CircleAlert className="size-4 shrink-0 text-amber-500" />}
                <span className="capitalize">{c.name}</span><span className="truncate font-mono text-xs text-muted">{c.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}

export function Overview() {
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard, retry: 1 });
  const d = dash.data;
  const exps = d ? Object.values(d.experiments.by_status).reduce((a, b) => a + b, 0) : 0;
  const available = d?.models.availability.available ?? 0;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Research overview</h1>
          <p className="mt-1 text-sm text-muted">See what AI sees. Detect what humans miss.</p>
        </div>
        {d && (d.reportable
          ? <Badge tone="emerald">reportable results stored</Badge>
          : <Badge tone="amber" title="No completed run on evaluation data without test doubles">development data only · nothing reportable</Badge>)}
      </div>

      {dash.isPending ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="dashboard-loading">
          {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : dash.isError || !d ? (
        <Card>
          <div className="flex items-start gap-2 p-4 text-sm" role="alert">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-red-500" />
            <div className="flex flex-col items-start gap-2">
              <p><span className="font-medium">Research summary unavailable.</span> <span className="text-muted">The dashboard reads stored data from the API; no figures are shown without it.</span></p>
              <Button onClick={() => void dash.refetch()}><RefreshCw className="size-3.5" /> Retry</Button>
            </div>
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Datasets" value={d.datasets.total} sub={`${d.datasets.frozen_versions} frozen of ${d.datasets.versions} version(s) · ${d.datasets.by_kind.evaluation ?? 0} evaluation`} to="/datasets" />
            <Stat label="Source records" value={d.datasets.sources} sub={`${nf.format(d.transforms.variants)} variants · ${d.transforms.recipes} recipe(s)`} to="/transforms" />
            <Stat label="Models installed" value={available} sub={`${d.models.catalogue} in catalogue${d.models.test_doubles ? ` · ${d.models.test_doubles} test double` : ""}`} to="/models" />
            <Stat label="Experiments" value={exps} sub={`${nf.format(d.experiments.outputs)} outputs · ${d.experiments.reportable} reportable`} to="/experiments" />
          </div>

          {d.datasets.sources === 0 && (
            <Card>
              <div className="flex flex-col items-start gap-3 p-4 text-sm" data-testid="dashboard-empty">
                <p className="text-muted">No datasets have been imported yet. Metrics appear here only after real data is stored and experiments have run.</p>
                <Link to="/datasets" className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 font-medium text-white hover:bg-violet-500">Import a dataset <ArrowRight className="size-3.5" /></Link>
              </div>
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <Card>
              <CardHeader title="Research readiness" actions={<span className="font-mono text-xs text-muted">{d.readiness.filter((r) => r.ok).length}/{d.readiness.length} met</span>} />
              <ReadinessList items={d.readiness} />
            </Card>
            <Card>
              <CardHeader title="Source records by language" />
              <div className="p-4"><Languages counts={d.languages} /></div>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card>
              <CardHeader title="Experiment states" />
              <ul className="flex flex-col gap-1.5 p-4 text-sm">
                {STATUS_ORDER.map((s) => (
                  <li key={s} className="flex items-center justify-between"><span className="text-muted">{s}</span><span className="font-mono tabular-nums">{d.experiments.by_status[s] ?? 0}</span></li>
                ))}
                <li className="mt-1 flex items-center justify-between border-t border-line pt-2"><span className="text-muted">failed outputs</span><span className="font-mono tabular-nums">{nf.format(d.experiments.failed_outputs)}</span></li>
                <li className="flex items-center justify-between"><span className="text-muted">test-double outputs</span><span className="font-mono tabular-nums">{nf.format(d.experiments.test_double_outputs)}</span></li>
              </ul>
            </Card>
            <Card>
              <CardHeader title="Transformations" />
              <div className="flex flex-col gap-3 p-4 text-sm">
                <p><span className="font-mono tabular-nums">{nf.format(d.transforms.variants)}</span> <span className="text-muted">variants, {nf.format(d.transforms.invalid_variants)} failed validation</span></p>
                {d.transforms.families.length ? (
                  <div className="flex flex-wrap gap-1.5">{d.transforms.families.map((f) => <Badge key={f} tone="violet">{f}</Badge>)}</div>
                ) : <p className="text-xs text-muted">No transformation families applied yet.</p>}
              </div>
            </Card>
            <Card>
              <CardHeader title="Pipeline" />
              <Pipeline d={d} />
            </Card>
          </div>
        </>
      )}

      <SystemStatus />
    </div>
  );
}
