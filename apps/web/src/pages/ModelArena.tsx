import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Cpu, FlaskConical, HardDrive, Play, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "../api/client";
import type { CapabilityName, InferResult, ModelInfo } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";

const TEXT_CAPS: CapabilityName[] = ["TOKENIZE", "CLASSIFY", "EMBED", "GENERATE"];

const AVAIL: Record<ModelInfo["availability"], { label: string; tone: "emerald" | "amber" | "red" | "neutral" }> = {
  available: { label: "available", tone: "emerald" },
  not_downloaded: { label: "not downloaded", tone: "amber" },
  dependency_missing: { label: "dependency missing", tone: "neutral" },
  resources_insufficient: { label: "insufficient resources", tone: "red" },
};

export function TestDoubleBanner() {
  return (
    <span className="inline-flex items-center gap-1 rounded border border-red-500/40 bg-red-500/10 px-1.5 py-0.5 font-mono text-[11px] text-red-600 dark:text-red-300">
      <ShieldAlert className="size-3" aria-hidden="true" /> TEST DOUBLE · not a model result
    </span>
  );
}

function ModelCard({ m }: { m: ModelInfo }) {
  return (
    <li className="flex min-w-0 flex-col gap-2 rounded-lg border border-line bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" title={m.key}>{m.key}</p>
          <p className="truncate font-mono text-[11px] text-muted" title={m.model_id}>{m.model_id}</p>
        </div>
        <Badge tone={AVAIL[m.availability].tone}>{AVAIL[m.availability].label}</Badge>
      </div>
      {m.test_double && <TestDoubleBanner />}
      <div className="flex flex-wrap gap-1">
        {m.capabilities.map((c) => <Badge key={c} tone="violet">{c}</Badge>)}
      </div>
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[11px]">
        <dt className="text-muted">Task</dt><dd className="font-mono">{m.task}</dd>
        <dt className="text-muted">Revision</dt><dd className="truncate font-mono" title={m.revision ?? ""}>{m.revision ?? "not pinned"}</dd>
        <dt className="text-muted">License</dt><dd className="truncate" title={m.license}>{m.license}</dd>
        <dt className="text-muted">Memory / disk</dt><dd className="font-mono">~{m.approx_ram_gb} GB / ~{m.approx_disk_gb} GB</dd>
        <dt className="text-muted">Languages</dt><dd className="font-mono">{m.languages.join(", ") || "—"}</dd>
      </dl>
      <p className="text-[11px] text-muted">{m.availability_detail}</p>
    </li>
  );
}

function ResultCard({ r }: { r: InferResult }) {
  const n = r.normalized;
  const scores = (r.raw_output as { scores?: Record<string, number> } | null)?.scores;
  return (
    <li className="flex min-w-0 flex-col gap-3 rounded-lg border border-line bg-surface p-4" data-testid="arena-result">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">{r.model}</span>
        {r.metadata.test_double && <TestDoubleBanner />}
        <span className="ml-auto font-mono text-xs text-muted">{r.latency_ms.toFixed(1)} ms · {r.metadata.device}</span>
      </div>
      {r.error ? (
        <p role="alert" className="text-sm text-red-500">{r.error.code}: {r.error.message}</p>
      ) : r.tokenization ? (
        <div className="flex flex-col gap-2">
          <p className="font-mono text-xs text-muted">{r.tokenization.tokens.length} tokens · {r.tokenization.unknown} unknown</p>
          <ul className="flex flex-wrap gap-1" aria-label={`${r.model} tokens`}>
            {r.tokenization.tokens.map((t, i) => (
              <li key={i} className="rounded border border-cyan-500/30 bg-cyan-500/5 px-1.5 py-0.5 font-mono text-xs">{t}</li>
            ))}
          </ul>
        </div>
      ) : r.capability === "CLASSIFY" ? (
        <div className="flex flex-col gap-1.5">
          <p className="text-sm">label <span className="font-mono">{String(n.label)}</span> · score <span className="font-mono">{Number(n.score).toFixed(3)}</span></p>
          {scores && Object.entries(scores).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[6rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-xs">
              <span className="truncate font-mono">{k}</span>
              <span className="h-1.5 rounded-full bg-surface-2"><span className="block h-1.5 rounded-full bg-violet-500/70" style={{ width: `${v * 100}%` }} /></span>
              <span className="text-right font-mono">{v.toFixed(3)}</span>
            </div>
          ))}
          <p className="text-[11px] text-muted">Scores are uncalibrated model outputs, not probabilities.</p>
        </div>
      ) : r.capability === "EMBED" ? (
        <p className="font-mono text-xs break-all">dim {String(n.dim)} · [{(r.raw_output as number[]).slice(0, 6).map((x) => x.toFixed(3)).join(", ")}, …]</p>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{String(n.text ?? "")}</p>
      )}
      <p className="font-mono text-[10px] text-muted">{r.metadata.model_id} @ {r.metadata.revision ?? "unpinned"} · adapter {r.metadata.adapter_version}</p>
    </li>
  );
}

export function ModelArena() {
  const models = useQuery({ queryKey: ["models"], queryFn: api.models });
  const [text, setText] = useState("kal milte hain 👍");
  const [cap, setCap] = useState<CapabilityName>("TOKENIZE");
  const [selected, setSelected] = useState<string[]>([]);
  const run = useMutation<InferResult[], ApiError, void>({
    mutationFn: () => Promise.all(selected.map((k) => api.infer(k, cap, text))),
  });
  const eligible = (models.data?.models ?? []).filter((m) => m.capabilities.includes(cap));
  const usable = eligible.filter((m) => m.availability === "available");

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Model Arena</h1>
          <p className="mt-1 text-sm text-muted">Compare tokenization, classification, embeddings and generation across locally installed models.</p>
        </div>
        {models.data && (
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge tone="cyan"><Cpu className="mr-1 size-3" />{models.data.device}</Badge>
            <span className="text-muted">{models.data.device_reason}</span>
            <Badge><HardDrive className="mr-1 size-3" />{models.data.resources.free_disk_gb} GB free</Badge>
            <Badge>RAM {models.data.resources.available_ram_gb === null ? "unknown" : `${models.data.resources.available_ram_gb.toFixed(1)} GB free`}</Badge>
          </div>
        )}
      </div>

      <Card>
        <CardHeader title="Model registry" actions={<span className="text-xs text-muted">{models.data ? `${models.data.models.filter((m) => m.availability === "available").length} of ${models.data.models.length} available` : ""}</span>} />
        {models.isPending ? (
          <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>
        ) : models.isError ? (
          <div className="flex items-center gap-3 p-4 text-sm"><span role="alert" className="text-red-500">{models.error.message}</span><Button onClick={() => void models.refetch()}>Retry</Button></div>
        ) : (
          <ul className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Models">
            {models.data.models.map((m) => <ModelCard key={m.key} m={m} />)}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader title="Compare" />
        <div className="flex flex-col gap-4 p-4">
          <label htmlFor="arena-input" className="sr-only">Input text</label>
          <textarea id="arena-input" rows={2} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}
            className="w-full rounded-md border border-line bg-surface-2 p-3 text-base outline-none focus:border-violet-500" />
          <div className="flex flex-wrap items-center gap-4">
            <div role="radiogroup" aria-label="Capability" className="flex rounded-md border border-line p-0.5">
              {TEXT_CAPS.map((c) => (
                <button key={c} type="button" role="radio" aria-checked={cap === c} onClick={() => { setCap(c); setSelected([]); }}
                  className={clsx("rounded px-2.5 py-1 font-mono text-xs", cap === c ? "bg-violet-600 text-white" : "text-muted hover:text-fg")}>{c}</button>
              ))}
            </div>
            <fieldset className="flex flex-wrap gap-3">
              <legend className="sr-only">Models</legend>
              {eligible.map((m) => (
                <label key={m.key} className={clsx("flex items-center gap-1.5 text-sm", m.availability !== "available" && "text-muted")} title={m.availability_detail}>
                  <input type="checkbox" disabled={m.availability !== "available"} checked={selected.includes(m.key)}
                    onChange={(e) => setSelected((s) => (e.target.checked ? [...s, m.key] : s.filter((x) => x !== m.key)))} />
                  {m.key}
                </label>
              ))}
            </fieldset>
            <Button variant="primary" className="ml-auto" disabled={selected.length === 0 || run.isPending} onClick={() => run.mutate()}>
              <Play className="size-3.5" /> {run.isPending ? "Running…" : "Run"}
            </Button>
          </div>
          {models.data && usable.length === 0 && (
            <div className="flex items-start gap-3 rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-sm" data-testid="no-models">
              <FlaskConical className="mt-0.5 size-4 shrink-0 text-amber-500" />
              <p>No installed model supports {cap} yet. Follow <code className="font-mono text-xs">docs/MODEL_SETUP_M4.md</code> to download and pin models on the target machine. Nothing is simulated in their place.</p>
            </div>
          )}
          {run.isError && <p role="alert" className="text-sm text-red-500">{run.error.code}: {run.error.message}</p>}
          {run.data && <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2" aria-label="Results">{run.data.map((r) => <ResultCard key={r.model} r={r} />)}</ul>}
        </div>
      </Card>
    </div>
  );
}
