import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { AlertTriangle, Scale } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "../api/client";
import type { GuardEvaluationResult, MetricsRow } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";

const f = (x: number | null | undefined) => (x === null || x === undefined ? "—" : x.toFixed(3));
const field = "w-full min-w-0 rounded-md border border-line bg-surface-2 px-2 py-1 text-sm";

function Confusion({ m }: { m: MetricsRow }) {
  return (
    <table className="text-center font-mono text-xs" aria-label="Confusion matrix">
      <thead><tr><th /><th scope="col" className="px-2 text-muted">pred 1</th><th scope="col" className="px-2 text-muted">pred 0</th></tr></thead>
      <tbody>
        <tr><th scope="row" className="pr-2 text-muted">true 1</th><td className="bg-emerald-500/15 px-3 py-1">{m.tp}</td><td className="bg-red-500/15 px-3 py-1">{m.fn}</td></tr>
        <tr><th scope="row" className="pr-2 text-muted">true 0</th><td className="bg-amber-500/15 px-3 py-1">{m.fp}</td><td className="bg-surface-2 px-3 py-1">{m.tn}</td></tr>
      </tbody>
    </table>
  );
}

function Results({ ev }: { ev: GuardEvaluationResult }) {
  const names = Object.keys(ev.results.systems);
  const [sel, setSel] = useState(names.find((n) => n === "emojiguard_full") ?? names[0] ?? "");
  const [stratum, setStratum] = useState("language");
  const s = ev.results.systems[sel];
  return (
    <>
      {!ev.research_reportable && (
        <div role="note" className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-sm" data-testid="eval-not-reportable">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-red-500" />Synthetic fixture evaluation: checks the pipeline only and is not a research result.
        </div>
      )}
      <Card>
        <CardHeader title="Baselines and ablations" actions={<span className="font-mono text-xs text-muted">split {String(ev.config.split)} · threshold {String(ev.config.decision_threshold)}</span>} />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" aria-label="System comparison">
            <thead className="text-xs text-muted"><tr className="border-b border-line">{["System", "Kind", "Precision", "Recall", "F1 (95% CI)", "FPR", "FNR", "Latency ms", "n"].map((h) => <th key={h} scope="col" className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>)}</tr></thead>
            <tbody className="font-mono text-xs">
              {names.map((n) => {
                const m = ev.results.systems[n]!.overall;
                return (
                  <tr key={n} className={clsx("cursor-pointer border-b border-line/60 hover:bg-surface-2", sel === n && "bg-violet-500/10")} onClick={() => setSel(n)} aria-selected={sel === n}>
                    <td className="px-3 py-1.5 font-sans">{n}</td>
                    <td className="px-3 py-1.5"><Badge tone={ev.results.systems[n]!.kind === "baseline" ? "neutral" : "violet"}>{ev.results.systems[n]!.kind}</Badge></td>
                    <td className="px-3 py-1.5">{f(m.precision)}</td><td className="px-3 py-1.5">{f(m.recall)}</td>
                    <td className="px-3 py-1.5 whitespace-nowrap">{f(m.f1)} [{f(m.f1_ci[0])}, {f(m.f1_ci[1])}]</td>
                    <td className="px-3 py-1.5">{f(m.fpr)}</td><td className="px-3 py-1.5">{f(m.fnr)}</td><td className="px-3 py-1.5">{f(m.mean_latency_ms)}</td><td className="px-3 py-1.5">{m.n}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {Object.keys(ev.results.unavailable).length > 0 && (
          <ul className="border-t border-line px-4 py-2 text-xs text-muted">{Object.entries(ev.results.unavailable).map(([k, v]) => <li key={k}><span className="font-mono">{k}</span>: unavailable ({v})</li>)}</ul>
        )}
      </Card>
      {s && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[auto_minmax(0,1fr)]">
          <Card><CardHeader title={sel} /><div className="p-4"><Confusion m={s.overall} /></div></Card>
          <Card className="min-w-0">
            <CardHeader title="By stratum" actions={
              <select aria-label="Stratum" className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={stratum} onChange={(e) => setStratum(e.target.value)}>
                <option value="language">language</option><option value="family">family</option>
              </select>} />
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-muted"><tr className="border-b border-line">{["Value", "n", "TP", "FP", "TN", "FN", "FPR", "F1"].map((h) => <th key={h} scope="col" className="px-3 py-1.5 font-medium">{h}</th>)}</tr></thead>
              <tbody>{Object.entries(s.strata[stratum] ?? {}).map(([k, m]) => (
                <tr key={k} className="border-b border-line/60"><td className="px-3 py-1">{k}</td><td className="px-3">{m.n}</td><td className="px-3">{m.tp}</td><td className="px-3">{m.fp}</td><td className="px-3">{m.tn}</td><td className="px-3">{m.fn}</td><td className="px-3">{f(m.fpr)}</td><td className="px-3">{f(m.f1)}</td></tr>
              ))}</tbody>
            </table>
          </Card>
        </div>
      )}
      {s && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {(["false_positives", "false_negatives"] as const).map((k) => (
            <Card key={k} className="min-w-0">
              <CardHeader title={`${k === "false_positives" ? "False positives" : "False negatives"} (${s.overall[k].length})`} />
              <ul className="max-h-72 divide-y divide-line overflow-auto" aria-label={k}>
                {s.overall[k].length === 0 ? <li className="p-4 text-sm text-muted">None.</li> : s.overall[k].map((id) => {
                  const it = ev.results.items[id];
                  return <li key={id} className="flex flex-col gap-0.5 px-4 py-2 text-sm"><span className="font-mono text-[11px] text-muted">{id} · {it?.language} · {it?.family}</span><span className="break-words">{it?.text}</span></li>;
                })}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

export function EvaluationDashboard() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["guard-evals"], queryFn: api.guardEvaluations });
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const detectors = useQuery({ queryKey: ["detectors"], queryFn: api.detectors });
  const [picked, setPicked] = useState<number | null>(null);
  const id = picked ?? list.data?.[0]?.id ?? null;
  const ev = useQuery({ queryKey: ["guard-eval", id], queryFn: () => api.guardEvaluation(id!), enabled: id !== null });
  const [target, setTarget] = useState("");
  const [keywords, setKeywords] = useState("");
  const [detectorId, setDetectorId] = useState("");
  const [slug, n] = target ? [target.split("@")[0] ?? "", Number(target.split("@")[1])] : ["", 0];
  const recipes = useQuery({ queryKey: ["recipes", slug, n], queryFn: () => api.recipes(slug, n), enabled: Boolean(target) });
  const frozen = (datasets.data ?? []).flatMap((d) => d.versions.filter((v) => v.frozen_at).map((v) => ({ key: `${d.slug}@${v.number}`, label: `${d.name} v${v.number}` })));
  const body = () => ({ dataset: slug, version: n, recipe_hashes: recipes.data?.map((r) => r.recipe_hash) ?? [], keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean), detector_id: detectorId ? Number(detectorId) : null });
  const runEval = useMutation<GuardEvaluationResult, ApiError, void>({
    mutationFn: () => api.runGuardEvaluation({ ...body(), split: "test" }),
    onSuccess: (r) => { void qc.invalidateQueries({ queryKey: ["guard-evals"] }); setPicked(r.id); qc.setQueryData(["guard-eval", r.id], r); },
  });
  const train = useMutation<{ id: number }, ApiError, void>({
    mutationFn: () => { const { dataset, version, recipe_hashes } = body(); return api.trainDetector({ dataset, version, recipe_hashes }); },
    onSuccess: (d) => { void qc.invalidateQueries({ queryKey: ["detectors"] }); setDetectorId(String(d.id)); },
  });
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Evaluation Dashboard</h1>
        <p className="mt-1 text-sm text-muted">EmojiGuard against baselines and ablations on a held-out, group-aware split. Labels are constructive transformation labels, not human judgments.</p>
      </div>
      <Card>
        <CardHeader title="New evaluation" />
        <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="flex flex-col gap-1 text-xs text-muted">Frozen version<select className={field} value={target} onChange={(e) => setTarget(e.target.value)}><option value="">Select…</option>{frozen.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</select></label>
          <label className="flex flex-col gap-1 text-xs text-muted">Keyword baseline (comma-separated)<input className={field} value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="password, login" /></label>
          <label className="flex flex-col gap-1 text-xs text-muted">Detector<select className={field} value={detectorId} onChange={(e) => setDetectorId(e.target.value)}><option value="">none</option>{detectors.data?.map((d) => <option key={d.id} value={d.id}>#{d.id} {d.version}</option>)}</select></label>
          <div className="flex flex-wrap items-end gap-2">
            <Button disabled={!target || !recipes.data?.length || train.isPending} onClick={() => train.mutate()}>Train detector (train split)</Button>
            <Button variant="primary" disabled={!target || !recipes.data?.length || runEval.isPending} onClick={() => runEval.mutate()}><Scale className="size-3.5" />{runEval.isPending ? "Running…" : "Evaluate (test split)"}</Button>
          </div>
          {target && <p className="text-xs text-muted md:col-span-2 xl:col-span-4">{recipes.data?.length ? `${recipes.data.length} recipe(s): ${recipes.data.map((r) => r.families).join(", ")}` : "No variants for this version yet."}</p>}
          {(runEval.isError || train.isError) && <p role="alert" className="text-sm text-red-500 md:col-span-2 xl:col-span-4">{(runEval.error ?? train.error)?.message}</p>}
        </div>
      </Card>
      {list.isPending ? <Skeleton className="h-20" /> : list.data?.length === 0 ? (
        <Card><p className="p-8 text-center text-sm text-muted" data-testid="eval-empty">No evaluations yet. Choose a frozen version with variants and run one.</p></Card>
      ) : (
        <>
          <label className="flex items-center gap-2 text-xs text-muted">Evaluation
            <select className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={id ?? ""} onChange={(e) => setPicked(Number(e.target.value))}>
              {list.data?.map((e) => <option key={e.id} value={e.id}>#{e.id} {String(e.config.dataset)} v{String(e.config.version)} · {new Date(e.created_at).toLocaleString()}</option>)}
            </select>
          </label>
          {ev.data && <Results key={ev.data.id} ev={ev.data} />}
        </>
      )}
      <p className="text-xs text-muted">Decision threshold = review threshold of the default policy. Risk scores are unvalidated and detector scores uncalibrated; see research limitations.</p>
    </div>
  );
}
