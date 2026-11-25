import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { AlertTriangle, Calculator, FlaskConical } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, api } from "../api/client";
import type { CRSCResult, MetricRow } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";

const STRATA = [
  ["language", "Language"],
  ["family", "Transformation"],
  ["modality", "Modality"],
  ["human", "Human equivalence"],
] as const;
const fmt = (x: number | null | undefined, d = 3) => (x === null || x === undefined ? "—" : x.toFixed(d));

function CI({ r }: { r: MetricRow }) {
  return (
    <span className="font-mono text-xs text-muted">
      95% CI [{fmt(r.ci_low)}, {fmt(r.ci_high)}] · n={r.n} · groups={r.n_groups}
    </span>
  );
}

function ModelSummary({ model, rows }: { model: string; rows: MetricRow[] }) {
  const sem = rows.find((r) => r.metric === "crsc_sem" && r.stratum === "overall" && r.model === model);
  const safe = rows.find((r) => r.metric === "crsc_safe" && r.stratum === "overall" && r.model === model);
  return (
    <li className="grid grid-cols-1 gap-4 rounded-lg border border-line bg-surface p-4 md:grid-cols-2" aria-label={`${model} summary`}>
      <div className="flex flex-col gap-1">
        <p className="text-xs text-muted">CRSC-sem · {model}</p>
        <p className="font-mono text-3xl font-semibold tabular-nums" data-testid={`sem-${model}`}>{fmt(sem?.value)}</p>
        {sem && <CI r={sem} />}
        {sem && <p className="text-xs text-muted">missing {sem.details.missing ?? 0} · identity pairs {sem.details.identity_pairs ?? 0} · identity failures{" "}
          <span className={clsx((sem.details.identity_failures ?? 0) > 0 && "font-semibold text-red-500")}>{sem.details.identity_failures ?? 0}</span></p>}
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-xs text-muted">CRSC-safe · {model}</p>
        <p className="font-mono text-3xl font-semibold tabular-nums" data-testid={`safe-${model}`}>{fmt(safe?.value)}</p>
        {safe && <CI r={safe} />}
        {safe && (
          <dl className="mt-1 grid grid-cols-3 gap-2 text-xs">
            <div><dt className="text-muted">unsafe→safe</dt><dd className="font-mono text-red-500">{safe.details.unsafe_to_safe ?? 0}</dd></div>
            <div><dt className="text-muted">safe→unsafe</dt><dd className="font-mono text-amber-600 dark:text-amber-300">{safe.details.safe_to_unsafe ?? 0}</dd></div>
            <div><dt className="text-muted">flip baseline</dt><dd className="font-mono">{fmt(safe.details.flip_rate)}</dd></div>
            <div><dt className="text-muted">unknown</dt><dd className="font-mono">{safe.details.unknown ?? 0}</dd></div>
            <div><dt className="text-muted">missing</dt><dd className="font-mono">{safe.details.missing ?? 0}</dd></div>
          </dl>
        )}
      </div>
    </li>
  );
}

function StratumChart({ rows, metric, stratum, model }: { rows: MetricRow[]; metric: MetricRow["metric"]; stratum: string; model: string }) {
  const data = rows
    .filter((r) => r.metric === metric && r.stratum === stratum && r.model === model)
    .map((r) => ({
      name: r.stratum_value,
      value: r.value,
      err: r.value !== null && r.ci_low !== null && r.ci_high !== null ? [r.value - r.ci_low, r.ci_high - r.value] : [0, 0],
      row: r,
    }));
  if (data.length === 0) return <p className="p-4 text-sm text-muted">No pairs in this stratum.</p>;
  const domainMin = metric === "crsc_sem" ? -1 : 0;
  return (
    <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <figure aria-label={`${metric} by ${stratum} for ${model}`} className="h-64 min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--border)" />
            <YAxis domain={[domainMin, 1]} tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--border)" width={36} />
            <Tooltip
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
              formatter={(v: unknown) => [typeof v === "number" ? v.toFixed(3) : "—", metric === "crsc_sem" ? "CRSC-sem" : "CRSC-safe"]}
            />
            <Bar dataKey="value" fill={metric === "crsc_sem" ? "#8b5cf6" : "#22d3ee"} radius={[4, 4, 0, 0]} isAnimationActive={false}>
              <ErrorBar dataKey="err" width={6} stroke="var(--text)" strokeWidth={1.2} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </figure>
      <table className="w-full self-start text-left text-xs">
        <caption className="sr-only">Exact values</caption>
        <thead className="text-muted"><tr className="border-b border-line"><th scope="col" className="py-1">Stratum</th><th scope="col">Value</th><th scope="col">95% CI</th><th scope="col">n / groups</th></tr></thead>
        <tbody className="font-mono">
          {data.map((d) => (
            <tr key={d.name} className="border-b border-line/60">
              <td className="py-1">{d.name}</td><td>{fmt(d.row.value)}</td><td>[{fmt(d.row.ci_low)}, {fmt(d.row.ci_high)}]</td><td>{d.row.n} / {d.row.n_groups}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Results({ data }: { data: CRSCResult }) {
  const models = [...new Set(data.results.map((r) => r.model))];
  const [model, setModel] = useState(models[0] ?? "");
  const [stratum, setStratum] = useState<string>("language");
  const [metric, setMetric] = useState<MetricRow["metric"]>("crsc_sem");
  return (
    <>
      <ul className="flex flex-col gap-3" aria-label="Model summaries">
        {models.map((m) => <ModelSummary key={m} model={m} rows={data.results} />)}
      </ul>
      <Card>
        <CardHeader
          title="Stratified results"
          actions={
            <div className="flex flex-wrap items-center gap-2">
              {models.length > 1 && (
                <select aria-label="Model" className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={model} onChange={(e) => setModel(e.target.value)}>
                  {models.map((m) => <option key={m}>{m}</option>)}
                </select>
              )}
              <div role="radiogroup" aria-label="Metric" className="flex rounded-md border border-line p-0.5">
                {(["crsc_sem", "crsc_safe"] as const).map((m) => (
                  <button key={m} type="button" role="radio" aria-checked={metric === m} onClick={() => setMetric(m)}
                    className={clsx("rounded px-2 py-0.5 font-mono text-xs", metric === m ? "bg-violet-600 text-white" : "text-muted")}>{m === "crsc_sem" ? "CRSC-sem" : "CRSC-safe"}</button>
                ))}
              </div>
            </div>
          }
        />
        <div role="tablist" aria-label="Stratum" className="flex flex-wrap gap-1 border-b border-line px-3 pt-2">
          {STRATA.map(([k, label]) => (
            <button key={k} type="button" role="tab" aria-selected={stratum === k} onClick={() => setStratum(k)}
              className={clsx("-mb-px border-b-2 px-2.5 py-1.5 text-sm", stratum === k ? "border-violet-500" : "border-transparent text-muted hover:text-fg")}>{label}</button>
          ))}
        </div>
        <StratumChart rows={data.results} metric={metric} stratum={stratum} model={model} />
      </Card>
    </>
  );
}

export function CRSCAnalytics() {
  const qc = useQueryClient();
  const experiments = useQuery({ queryKey: ["experiments"], queryFn: api.experiments });
  const completed = (experiments.data ?? []).filter((e) => e.status === "completed");
  const [picked, setPicked] = useState<number | null>(null);
  const id = picked ?? completed[0]?.id ?? null;
  const [resamples, setResamples] = useState(2000);
  const [seed, setSeed] = useState(0);
  const crsc = useQuery({ queryKey: ["crsc", id], queryFn: () => api.crsc(id!), enabled: id !== null });
  const compute = useMutation<CRSCResult, ApiError, void>({
    mutationFn: () => api.computeCrsc(id!, resamples, seed),
    onSuccess: (d) => qc.setQueryData(["crsc", id], d),
  });
  const data = crsc.data;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">CRSC Analytics <Badge tone="amber">experimental</Badge></h1>
          <p className="mt-1 text-sm text-muted">Cross-Representation Security Consistency, reported as two separate metrics with source-group bootstrap intervals.</p>
        </div>
        <Link to="/experiments" className="text-sm text-violet-500 hover:underline">Inspect stored outputs →</Link>
      </div>

      {experiments.isPending ? <Skeleton className="h-24" /> : completed.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center gap-2 p-10 text-center text-sm text-muted" data-testid="crsc-empty">
            <FlaskConical className="size-6" />
            No completed experiments yet. CRSC is computed only from stored outputs of a completed experiment.
            <Link to="/experiments" className="text-violet-500 hover:underline">Open the Experiment Studio</Link>
          </div>
        </Card>
      ) : (
        <>
          <Card>
            <div className="flex flex-wrap items-end gap-3 p-4">
              <label className="flex flex-col gap-1 text-xs text-muted">Experiment
                <select className="rounded-md border border-line bg-surface-2 px-2 py-1 text-sm" value={id ?? ""} onChange={(e) => setPicked(Number(e.target.value))}>
                  {completed.map((e) => <option key={e.id} value={e.id}>#{e.id} {e.name}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-xs text-muted">Bootstrap resamples
                <input type="number" min={100} max={20000} step={100} value={resamples} onChange={(e) => setResamples(Number(e.target.value))} className="w-28 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-sm" />
              </label>
              <label className="flex flex-col gap-1 text-xs text-muted">Seed
                <input type="number" min={0} value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="w-24 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-sm" />
              </label>
              <Button variant="primary" onClick={() => compute.mutate()} disabled={compute.isPending}>
                <Calculator className="size-3.5" /> {compute.isPending ? "Computing…" : "Compute CRSC"}
              </Button>
              {data?.computed_at && <span className="font-mono text-xs text-muted">v{data.crsc_version} · {data.resamples} resamples · seed {data.seed} · {new Date(data.computed_at).toLocaleString()}</span>}
            </div>
            {compute.isError && <p role="alert" className="px-4 pb-4 text-sm text-red-500">{compute.error.code}: {compute.error.message}</p>}
          </Card>
          {data && !data.research_reportable && data.results.length > 0 && (
            <div role="note" className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm" data-testid="not-reportable">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-500" />
              <p>Not research-reportable: {[data.synthetic_fixture && "computed on a synthetic fixture dataset", data.test_double && "includes test-double model outputs"].filter(Boolean).join(" and ")}. Use only to check the pipeline.</p>
            </div>
          )}
          {crsc.isPending ? <Skeleton className="h-40" /> : data && data.results.length === 0 ? (
            <Card className="p-8 text-center text-sm text-muted">Not computed yet for this experiment. Choose resamples and a seed, then compute.</Card>
          ) : data ? <Results key={`${data.experiment_id}-${data.computed_at}`} data={data} /> : null}
          <p className="text-xs text-muted">
            CRSC-sem is a mean cosine similarity of embeddings, not proof of equal meaning. CRSC-safe uses decidable pairs only; flips, unknown and missing are reported separately. See research/CRSC_SPECIFICATION.md.
          </p>
        </>
      )}
    </div>
  );
}
