import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Ban, FlaskConical, Play, RotateCcw } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ApiError, api } from "../api/client";
import type { ExperimentRow, ExperimentStatus } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";
import { TestDoubleBanner } from "./ModelArena";

const STATUS_TONE: Record<ExperimentStatus, "neutral" | "cyan" | "amber" | "emerald" | "red" | "violet"> = {
  queued: "neutral",
  running: "cyan",
  cancelling: "amber",
  cancelled: "amber",
  completed: "emerald",
  failed: "red",
  interrupted: "red",
};
const TEXT_CAPS = ["TOKENIZE", "CLASSIFY", "EMBED", "GENERATE"];
const MODALITIES: { id: string; label: string; help: string }[] = [
  { id: "text", label: "text", help: "the stored text" },
  { id: "ocr", label: "ocr", help: "rendered, then read back by Tesseract" },
  { id: "vlm", label: "vlm", help: "rendered image sent to VISION_INPUT models" },
];
const ACTIVE: ExperimentStatus[] = ["queued", "running", "cancelling"];
const field = "w-full min-w-0 rounded-md border border-line bg-surface-2 px-2 py-1 text-sm";

function Progress({ e }: { e: ExperimentRow }) {
  const pct = e.total_items ? Math.round((e.done_items / e.total_items) * 100) : 0;
  return (
    <div className="flex items-center gap-2" aria-label={`progress ${pct}%`}>
      <div className="h-1.5 w-28 rounded-full bg-surface-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={clsx("h-1.5 rounded-full", e.status === "failed" || e.status === "interrupted" ? "bg-red-500/70" : "bg-violet-500/80")} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[11px] text-muted">{e.done_items}/{e.total_items}</span>
    </div>
  );
}

function NewExperiment({ onCreated }: { onCreated: (id: number) => void }) {
  const qc = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const models = useQuery({ queryKey: ["models"], queryFn: api.models });
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [modelKeys, setModelKeys] = useState<string[]>([]);
  const [caps, setCaps] = useState<string[]>(["CLASSIFY"]);
  const [recipes, setRecipes] = useState<string[]>([]);
  const [labelMap, setLabelMap] = useState("");
  const [modalities, setModalities] = useState<string[]>(["text"]);
  const [vlmPrompt, setVlmPrompt] = useState("");
  const [slug, n] = target ? [target.split("@")[0] ?? "", Number(target.split("@")[1])] : ["", 0];
  const recipeList = useQuery({ queryKey: ["recipes", slug, n], queryFn: () => api.recipes(slug, n), enabled: Boolean(target) });
  const frozen = (datasets.data ?? []).flatMap((d) => d.versions.filter((v) => v.frozen_at).map((v) => ({ key: `${d.slug}@${v.number}`, label: `${d.name} v${v.number}`, kind: d.kind })));
  const available = (models.data?.models ?? []).filter((m) => m.availability === "available" && m.capabilities.some((c) => [...TEXT_CAPS, "VISION_INPUT"].includes(c)));
  const create = useMutation<ExperimentRow, ApiError, void>({
    mutationFn: () => {
      const map = Object.fromEntries(labelMap.split("\n").map((l) => l.split("=").map((x) => x.trim())).filter((p) => p.length === 2 && p[0] && (p[1] === "safe" || p[1] === "unsafe")));
      return api.createExperiment({
        name, dataset: slug, version: n, recipe_hashes: recipes, model_keys: modelKeys,
        capabilities: sentCaps, modalities,
        label_map: canMapSafety && Object.keys(map).length ? map : null,
        ...(wantsVlm && vlmPrompt.trim() ? { vlm_prompt: vlmPrompt.trim() } : {}),
      });
    },
    onSuccess: (e) => { void qc.invalidateQueries({ queryKey: ["experiments"] }); onCreated(e.id); },
  });
  const toggle = (list: string[], set: (v: string[]) => void, v: string) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };
  const kind = frozen.find((f) => f.key === target)?.kind;
  const safetyModels = available.filter((m) => modelKeys.includes(m.key) && m.task === "safety");
  const wantsVlm = modalities.includes("vlm");
  const textModalities = modalities.some((m) => m !== "vlm");
  // VISION_INPUT runs only with the vlm modality, so it follows that choice rather than a checkbox.
  const sentCaps = [...(textModalities ? caps : []), ...(wantsVlm ? ["VISION_INPUT"] : [])];
  const canMapSafety = safetyModels.length > 0 && textModalities && caps.includes("CLASSIFY");
  const visionModels = available.filter((m) => modelKeys.includes(m.key) && m.capabilities.includes("VISION_INPUT"));
  const vlmProblem = wantsVlm && modelKeys.length > 0 && visionModels.length === 0 ? "None of the selected models accepts images (VISION_INPUT)." : null;

  return (
    <form onSubmit={submit} aria-label="New experiment" className="flex min-w-0 flex-col gap-4 p-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="flex min-w-0 flex-col gap-1 text-xs text-muted">Name<input required maxLength={200} className={field} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="flex flex-col gap-1 text-xs text-muted">Frozen dataset version
          <select required className={field} value={target} onChange={(e) => { setTarget(e.target.value); setRecipes([]); }}>
            <option value="">Select…</option>
            {frozen.map((f) => <option key={f.key} value={f.key}>{f.label}{f.kind === "synthetic_fixture" ? " (synthetic fixture)" : ""}</option>)}
          </select>
        </label>
      </div>
      {kind === "synthetic_fixture" && <p className="text-xs text-amber-600 dark:text-amber-300">Synthetic fixture dataset: results are for development and are excluded from research reporting.</p>}
      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1 text-xs font-medium text-muted">Variant recipes (sources are always included)</legend>
        {!target ? <p className="text-xs text-muted">Choose a version first.</p> : recipeList.data?.length === 0 ? <p className="text-xs text-muted">No variants yet; generate them in the Transformation Lab.</p> : recipeList.data?.map((r) => (
          <label key={r.recipe_hash} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={recipes.includes(r.recipe_hash)} onChange={() => toggle(recipes, setRecipes, r.recipe_hash)} />
            <span>{r.families}</span><span className="font-mono text-[11px] text-muted">seed {r.seed} · {r.variants} variants · {r.recipe_hash.slice(0, 10)}…</span>
          </label>
        ))}
      </fieldset>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1 text-xs font-medium text-muted">Models (installed only)</legend>
          {available.length === 0 ? <p className="text-xs text-muted" data-testid="no-available-models">No installed models. See docs/MODEL_SETUP_M4.md.</p> : available.map((m) => (
            <label key={m.key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={modelKeys.includes(m.key)} onChange={() => toggle(modelKeys, setModelKeys, m.key)} />
              {m.key} {m.test_double && <TestDoubleBanner />}
            </label>
          ))}
        </fieldset>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1 text-xs font-medium text-muted">Capabilities (text and ocr inputs)</legend>
          {TEXT_CAPS.map((c) => (
            <label key={c} className="flex items-center gap-2 font-mono text-xs"><input type="checkbox" disabled={!textModalities} checked={caps.includes(c)} onChange={() => toggle(caps, setCaps, c)} />{c}</label>
          ))}
          <p className="font-mono text-xs text-muted" data-testid="vision-cap">VISION_INPUT {wantsVlm ? "· on (vlm modality)" : "· off (select the vlm modality)"}</p>
        </fieldset>
      </div>
      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1 text-xs font-medium text-muted">Input modalities</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-1.5">
          {MODALITIES.map((m) => (
            <label key={m.id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={modalities.includes(m.id)} onChange={() => toggle(modalities, setModalities, m.id)} />
              <span className="font-mono text-xs">{m.label}</span><span className="text-xs text-muted">{m.help}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {wantsVlm && (
        <label className="flex flex-col gap-1 text-xs text-muted">VLM prompt (optional; default asks for an exact transcription)
          <input maxLength={300} className={field} value={vlmPrompt} onChange={(e) => setVlmPrompt(e.target.value)} placeholder="Transcribe the text in this image exactly." />
        </label>
      )}
      {vlmProblem && <p className="text-xs text-amber-600 dark:text-amber-300" data-testid="vlm-problem">{vlmProblem}</p>}
      <label className="flex flex-col gap-1 text-xs text-muted">SafetyJudge label map (safety classifiers only; one <code className="font-mono">label=safe|unsafe</code> per line)
        <textarea rows={2} disabled={!canMapSafety} className={`${field} font-mono text-xs disabled:opacity-50`} value={labelMap} onChange={(e) => setLabelMap(e.target.value)} placeholder={canMapSafety ? "label=unsafe" : "No selected safety classifier"} aria-describedby="labelmap-help" />
      </label>
      <p id="labelmap-help" className="text-xs text-muted" data-testid="labelmap-help">
        Only models whose task is <span className="font-mono">safety</span> can produce safety judgments. Sentiment, embedding and generation outputs are never mapped to safe/unsafe.
      </p>
      {create.isError && <p role="alert" className="text-sm text-red-500">{create.error.code}: {create.error.message}</p>}
      <Button type="submit" variant="primary" className="w-fit" disabled={!target || modelKeys.length === 0 || modalities.length === 0 || sentCaps.length === 0 || Boolean(vlmProblem) || create.isPending}>
        <Play className="size-3.5" /> Queue experiment
      </Button>
    </form>
  );
}

function Detail({ id }: { id: number }) {
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [page, setPage] = useState(1);
  const exp = useQuery({ queryKey: ["experiment", id], queryFn: () => api.experiment(id), refetchInterval: (q) => (q.state.data && ACTIVE.includes(q.state.data.status) ? 1500 : false) });
  const outs = useQuery({ queryKey: ["outputs", id, errorsOnly, page, exp.data?.done_items], queryFn: () => api.outputs(id, { page, page_size: 25, errors_only: errorsOnly }) });
  if (!exp.data) return <Skeleton className="m-4 h-24" />;
  const e = exp.data;
  const pages = outs.data ? Math.max(1, Math.ceil(outs.data.total / 25)) : 1;
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-semibold">#{e.id} {e.name}</h3>
        <Badge tone={STATUS_TONE[e.status]}>{e.status}</Badge>
        {e.uses_test_doubles && <TestDoubleBanner />}
        <Progress e={e} />
      </div>
      {e.error && <p role="alert" className="rounded-md border border-red-500/30 bg-red-500/5 p-2 text-xs">{e.error}</p>}
      <dl className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
        <div><dt className="text-muted">Config hash</dt><dd className="font-mono break-all">{e.config_hash}</dd></div>
        <div><dt className="text-muted">Failed items</dt><dd className="font-mono">{e.failed_items}</dd></div>
      </dl>
      <details className="text-xs"><summary className="cursor-pointer text-muted">Full configuration</summary><pre className="mt-2 overflow-auto rounded bg-surface-2 p-2 font-mono">{JSON.stringify(e.config, null, 2)}</pre></details>
      <div className="flex items-center gap-3">
        <h4 className="text-sm font-medium">Stored outputs</h4>
        <label className="flex items-center gap-1.5 text-xs"><input type="checkbox" checked={errorsOnly} onChange={(ev) => { setErrorsOnly(ev.target.checked); setPage(1); }} />errors only</label>
        <span className="ml-auto font-mono text-xs text-muted">{outs.data?.total ?? 0} rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-muted"><tr className="border-b border-line">{["Item", "Lang", "Split", "Model", "Cap", "Output", "Behaviour", "Safety", "ms"].map((h) => <th key={h} scope="col" className="px-2 py-1.5 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {outs.data?.items.map((o) => (
              <tr key={o.id} className="border-b border-line/60 align-top">
                <td className="max-w-56 px-2 py-1.5"><span className="font-mono">{o.source_id}{o.variant_id ? ` · v${o.variant_id}` : ""}</span><br /><span className="break-words">{o.input_text}</span></td>
                <td className="px-2 py-1.5 font-mono">{o.language}</td>
                <td className="px-2 py-1.5 font-mono">{o.split}</td>
                <td className="px-2 py-1.5 font-mono">{o.model_key}{o.test_double && <span className="block text-red-500">test double</span>}</td>
                <td className="px-2 py-1.5 font-mono">{o.capability}</td>
                <td className="max-w-64 px-2 py-1.5 font-mono break-words">{o.error ? <span className="text-red-500">{o.error.code}</span> : JSON.stringify(o.normalized).slice(0, 140)}</td>
                <td className="px-2 py-1.5 font-mono">{o.behavior ?? "—"}</td>
                <td className="px-2 py-1.5 font-mono">{o.safety ?? "—"}</td>
                <td className="px-2 py-1.5 font-mono">{o.latency_ms.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {outs.data?.items.length === 0 && <p className="p-3 text-sm text-muted">No outputs stored yet.</p>}
      </div>
      <div className="flex items-center justify-end gap-2 text-xs">
        <Button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>Previous</Button>
        <span className="font-mono">page {page} / {pages}</span>
        <Button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>Next</Button>
      </div>
    </div>
  );
}

export function ExperimentStudio() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);
  const list = useQuery({ queryKey: ["experiments"], queryFn: api.experiments, refetchInterval: (q) => (q.state.data?.some((e) => ACTIVE.includes(e.status)) ? 1500 : false) });
  const act = useMutation<ExperimentRow, ApiError, { id: number; action: "cancel" | "resume" }>({
    mutationFn: ({ id, action }) => (action === "cancel" ? api.cancelExperiment(id) : api.resumeExperiment(id)),
    onSuccess: (e) => { void qc.invalidateQueries({ queryKey: ["experiments"] }); void qc.invalidateQueries({ queryKey: ["experiment", e.id] }); },
  });
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Experiment Studio</h1>
        <p className="mt-1 text-sm text-muted">Configure, run, cancel and audit experiments. Every output is stored with model revision, parameters and timing.</p>
      </div>
      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[28rem_minmax(0,1fr)]">
        <Card className="min-w-0"><CardHeader title="New experiment" /><NewExperiment onCreated={setSelected} /></Card>
        <Card className="min-w-0">
          <CardHeader title="Experiment history" />
          {list.isPending ? <div className="p-4"><Skeleton className="h-16" /></div> : list.isError ? <p role="alert" className="p-4 text-sm text-red-500">{list.error.message}</p> : list.data.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-10 text-center text-sm text-muted" data-testid="no-experiments"><FlaskConical className="size-6" />No experiments yet. Configure one on the left once a model is installed and a dataset version is frozen.</div>
          ) : (
            <ul className="divide-y divide-line" aria-label="Experiments">
              {list.data.map((e) => (
                <li key={e.id} className={clsx("flex flex-wrap items-center gap-3 px-4 py-3", selected === e.id && "bg-violet-500/10")}>
                  <button type="button" className="min-w-0 flex-1 text-left" onClick={() => setSelected(e.id)} aria-current={selected === e.id}>
                    <span className="block truncate text-sm font-medium">#{e.id} {e.name}</span>
                    <span className="font-mono text-[11px] text-muted">{new Date(e.created_at).toLocaleString()}</span>
                  </button>
                  <Badge tone={STATUS_TONE[e.status]}>{e.status}</Badge>
                  <Progress e={e} />
                  {ACTIVE.includes(e.status) && e.status !== "cancelling" && <Button aria-label={`Cancel experiment ${e.id}`} onClick={() => act.mutate({ id: e.id, action: "cancel" })}><Ban className="size-3.5" /></Button>}
                  {["interrupted", "failed", "cancelled"].includes(e.status) && <Button aria-label={`Resume experiment ${e.id}`} onClick={() => act.mutate({ id: e.id, action: "resume" })}><RotateCcw className="size-3.5" /></Button>}
                </li>
              ))}
            </ul>
          )}
          {selected !== null && <div className="border-t border-line"><Detail key={selected} id={selected} /></div>}
        </Card>
      </div>
    </div>
  );
}
