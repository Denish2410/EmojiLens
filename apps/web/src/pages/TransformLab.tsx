import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowDown, ArrowUp, Play, Plus, ScanSearch, Trash2, Wand2 } from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import type { ApplyResult, ChainStepIn, GenerateResult, TransformSpec } from "../api/types";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";
import { countInvisible, revealInvisible } from "../lib/visible";

const VARIETIES = ["en", "hi", "gu", "hi-Latn", "gu-Latn"];

function defaults(spec: TransformSpec): Record<string, unknown> {
  return Object.fromEntries(spec.params.map((p) => [p.name, p.default]));
}

function ParamField({
  spec,
  name,
  value,
  onChange,
}: {
  spec: TransformSpec;
  name: string;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const p = spec.params.find((x) => x.name === name)!;
  const id = useId();
  const cls = "rounded-md border border-line bg-surface-2 px-2 py-1 text-xs";
  return (
    <label className="flex flex-col gap-1 text-xs text-muted" htmlFor={id} title={p.description}>
      {p.name}
      {p.kind === "choice" ? (
        <select id={id} className={cls} value={String(value)} onChange={(e) => onChange(e.target.value)}>
          {p.choices.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      ) : p.kind === "bool" ? (
        <input id={id} type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
      ) : p.kind === "float" ? (
        <input id={id} type="number" step={0.05} min={p.minimum ?? undefined} max={p.maximum ?? undefined}
          className={clsx(cls, "w-24 font-mono")} value={Number(value)}
          onChange={(e) => onChange(Number(e.target.value))} />
      ) : (
        <input id={id} type="text" maxLength={200} className={clsx(cls, "font-mono")} value={String(value)}
          onChange={(e) => onChange(e.target.value)} />
      )}
    </label>
  );
}

function GeneratePanel({ chain, seed }: { chain: ChainStepIn[]; seed: number }) {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const [target, setTarget] = useState("");
  const options = (datasets.data ?? []).flatMap((d) =>
    d.versions.filter((v) => v.frozen_at).map((v) => ({ key: `${d.slug}@${v.number}`, label: `${d.name} v${v.number}` })),
  );
  const gen = useMutation<GenerateResult, ApiError, string>({
    mutationFn: (key) => {
      const [slug, n] = key.split("@");
      return api.generateVariants(slug ?? "", Number(n), { seed, chain });
    },
  });
  return (
    <Card>
      <CardHeader title="Generate dataset variants" />
      <div className="flex flex-col gap-3 p-4 text-sm">
        <p className="text-xs text-muted">
          Applies this exact chain and seed to every source of a frozen dataset version. Variants inherit their source
          group&apos;s split, so they cannot leak across splits.
        </p>
        {options.length === 0 ? (
          <p className="text-xs text-muted">No frozen dataset versions yet. Freeze one in the Dataset Explorer first.</p>
        ) : (
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1 text-xs text-muted">
              Frozen version
              <select className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={target}
                onChange={(e) => setTarget(e.target.value)}>
                <option value="">Select…</option>
                {options.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
              </select>
            </label>
            <Button variant="primary" disabled={!target || chain.length === 0 || gen.isPending} onClick={() => gen.mutate(target)}>
              <Wand2 className="size-3.5" /> {gen.isPending ? "Generating…" : "Generate variants"}
            </Button>
          </div>
        )}
        {gen.isError && <p role="alert" className="text-xs text-red-500">{gen.error.code}: {gen.error.message}</p>}
        {gen.data && (
          <p className="font-mono text-xs" data-testid="generate-result">
            created {gen.data.created} · already existed {gen.data.skipped_existing} · invalid {gen.data.invalid} · recipe{" "}
            {gen.data.recipe_hash.slice(0, 12)}…
          </p>
        )}
      </div>
    </Card>
  );
}

export function TransformLab() {
  const navigate = useNavigate();
  const specs = useQuery({ queryKey: ["transforms"], queryFn: api.transforms });
  const [text, setText] = useState("Today the weather is very good, my friend 👍");
  const [variety, setVariety] = useState("en");
  const [seed, setSeed] = useState(7);
  const [chain, setChain] = useState<ChainStepIn[]>([]);
  const [adding, setAdding] = useState("homoglyph");
  const run = useMutation<ApplyResult, ApiError, void>({
    mutationFn: () => api.applyChain({ text, variety, seed, chain }),
  });
  const byId = useMemo(() => Object.fromEntries((specs.data ?? []).map((s) => [s.id, s])), [specs.data]);
  const r = run.data;

  const update = (i: number, step: ChainStepIn) => setChain((c) => c.map((s, j) => (j === i ? step : s)));
  const move = (i: number, d: -1 | 1) =>
    setChain((c) => {
      const n = [...c];
      const [x] = n.splice(i, 1);
      n.splice(i + d, 0, x!);
      return n;
    });

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Transformation Laboratory</h1>
        <p className="mt-1 text-sm text-muted">
          Build reproducible transformation chains for controlled, local, defensive evaluation. Payload parameters
          take harmless surrogate text only.
        </p>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <Card>
          <CardHeader title={<label htmlFor="tl-input">Original text</label>} />
          <textarea id="tl-input" rows={3} value={text} spellCheck={false} onChange={(e) => setText(e.target.value)}
            className="block w-full resize-y bg-transparent p-4 text-base outline-none" />
          <div className="flex flex-wrap items-end gap-3 border-t border-line px-4 py-3">
            <label className="flex flex-col gap-1 text-xs text-muted">
              Variety
              <select className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={variety}
                onChange={(e) => setVariety(e.target.value)}>
                {VARIETIES.map((v) => <option key={v}>{v}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted">
              Seed
              <input type="number" min={0} value={seed} onChange={(e) => setSeed(Number(e.target.value))}
                className="w-28 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-xs" />
            </label>
            <Button variant="primary" className="ml-auto" disabled={chain.length === 0 || run.isPending} onClick={() => run.mutate()}>
              <Play className="size-3.5" /> {run.isPending ? "Running…" : "Run chain"}
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader title={`Chain (${chain.length}/8)`} />
          <div className="flex flex-col gap-3 p-4">
            {specs.isPending ? (
              <Skeleton className="h-10 w-full" />
            ) : specs.isError ? (
              <p role="alert" className="text-sm text-red-500">{specs.error.message}</p>
            ) : (
              <div className="flex gap-2">
                <select aria-label="Transformation to add" className="min-w-0 flex-1 rounded-md border border-line bg-surface-2 px-2 py-1 text-xs"
                  value={adding} onChange={(e) => setAdding(e.target.value)}>
                  {specs.data.map((s) => <option key={s.id} value={s.id}>{s.family} · {s.id} v{s.version}</option>)}
                </select>
                <Button className="shrink-0" disabled={chain.length >= 8} onClick={() => byId[adding] && setChain((c) => [...c, { transform_id: adding, params: defaults(byId[adding]!) }])}>
                  <Plus className="size-3.5" /> Add
                </Button>
              </div>
            )}
            {chain.length === 0 && <p className="text-xs text-muted">Add one or more steps to build a chain.</p>}
            <ol className="flex flex-col gap-2" aria-label="Chain steps">
              {chain.map((step, i) => {
                const spec = byId[step.transform_id];
                if (!spec) return null;
                return (
                  <li key={i} className="rounded-md border border-line p-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted">{i + 1}.</span>
                      <span className="text-sm font-medium">{spec.id}</span>
                      <Badge>{spec.family}</Badge>
                      <span className="ml-auto flex gap-1">
                        <button type="button" aria-label={`Move step ${i + 1} up`} disabled={i === 0} onClick={() => move(i, -1)} className="rounded p-1 text-muted hover:bg-surface-2 disabled:opacity-30"><ArrowUp className="size-3.5" /></button>
                        <button type="button" aria-label={`Move step ${i + 1} down`} disabled={i === chain.length - 1} onClick={() => move(i, 1)} className="rounded p-1 text-muted hover:bg-surface-2 disabled:opacity-30"><ArrowDown className="size-3.5" /></button>
                        <button type="button" aria-label={`Remove step ${i + 1}`} onClick={() => setChain((c) => c.filter((_, j) => j !== i))} className="rounded p-1 text-muted hover:bg-surface-2"><Trash2 className="size-3.5" /></button>
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted">{spec.description}</p>
                    {spec.params.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-3">
                        {spec.params.map((p) => (
                          <ParamField key={p.name} spec={spec} name={p.name} value={step.params[p.name]}
                            onChange={(v) => update(i, { ...step, params: { ...step.params, [p.name]: v } })} />
                        ))}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        </Card>
      </div>

      {run.isError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm">
          <span className="font-mono text-red-500">{run.error.code}</span> {run.error.message}
        </div>
      )}

      {r && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {(
              [
                ["Original", r.original, r.original_sha256],
                ["Transformed", r.output, r.output_sha256],
              ] as const
            ).map(([label, value, sha]) => (
              <Card key={label}>
                <CardHeader title={label} actions={<Badge tone={countInvisible(value) ? "amber" : "neutral"}>invisible: {countInvisible(value)}</Badge>} />
                <div className="flex flex-col gap-2 p-4">
                  <p className="text-lg break-words whitespace-pre-wrap" data-testid={`${label.toLowerCase()}-text`}>{value}</p>
                  <p className="rounded bg-surface-2 p-2 font-mono text-xs break-all text-muted" aria-label={`${label} with invisible characters revealed`}>
                    {revealInvisible(value)}
                  </p>
                  <p className="font-mono text-[11px] break-all text-muted">sha256 {sha}</p>
                </div>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader
              title="Chain"
              actions={
                <Button onClick={() => navigate("/inspector", { state: { text: r.output } })}>
                  <ScanSearch className="size-3.5" /> Inspect output
                </Button>
              }
            />
            <ol className="flex flex-col divide-y divide-line">
              {r.steps.map((s, i) => (
                <li key={i} className="flex flex-col gap-2 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-muted">step {i + 1}</span>
                    <span className="text-sm font-medium">{s.transform_id} v{s.version}</span>
                    <Badge tone={s.valid ? "emerald" : "red"}>{s.valid ? "valid" : "invalid"}</Badge>
                    <span className="font-mono text-xs text-muted">edits {s.edits} · seed {s.seed}</span>
                  </div>
                  <p className="break-words">{s.output}</p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(s.checks).map(([k, v]) => (
                      <Badge key={k} tone={v === null ? "neutral" : v ? "emerald" : "amber"}>{k}: {v === null ? "n/a" : String(v)}</Badge>
                    ))}
                  </div>
                  {s.notes.map((n) => <p key={n} className="text-xs text-amber-600 dark:text-amber-300">{n}</p>)}
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted">Parameters and provenance</summary>
                    <pre className="mt-2 max-h-64 overflow-auto rounded bg-surface-2 p-2 font-mono">{JSON.stringify({ params: s.params, provenance: s.provenance }, null, 2)}</pre>
                  </details>
                </li>
              ))}
            </ol>
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Reproducibility" />
              <dl className="grid gap-2 p-4 text-xs">
                <div><dt className="text-muted">Chain hash (seed, variety, step ids, versions, resolved params)</dt><dd className="font-mono break-all" data-testid="chain-hash">{r.chain_hash}</dd></div>
                <div><dt className="text-muted">Seed · variety</dt><dd className="font-mono">{r.seed} · {r.variety}</dd></div>
                <div><dt className="text-muted">Overall validity</dt><dd className="font-mono">{String(r.valid)}</dd></div>
              </dl>
            </Card>
            <Card>
              <CardHeader title="Offset map (original → output)" />
              <div className="max-h-72 overflow-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-muted"><tr className="border-b border-line"><th scope="col" className="px-3 py-1.5">Original cp</th><th scope="col" className="px-3 py-1.5">Original</th><th scope="col" className="px-3 py-1.5">Output</th></tr></thead>
                  <tbody className="font-mono">
                    {r.pieces.slice(0, 300).map(([s, e, t], i) => {
                      const orig = Array.from(r.original).slice(s, e).join("");
                      return (
                        <tr key={i} className={clsx("border-b border-line/60", orig !== t && "bg-cyan-500/10")}>
                          <td className="px-3 py-1">{s}–{e}</td>
                          <td className="px-3 py-1 font-sans">{revealInvisible(orig)}</td>
                          <td className="px-3 py-1 font-sans">{revealInvisible(t) || <span className="text-red-400">(removed)</span>}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}

      <GeneratePanel chain={chain} seed={seed} />
    </div>
  );
}
