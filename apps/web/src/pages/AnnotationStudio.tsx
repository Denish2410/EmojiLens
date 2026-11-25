import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ApiError, api } from "../api/client";
import { Distribution } from "../components/Distribution";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, CardHeader } from "../components/ui";

const VARIETIES = ["en", "hi", "gu", "hi-Latn", "gu-Latn"] as const;
const SEMANTIC = [
  ["equivalent", "Equivalent: same meaning"],
  ["partial", "Partial: some meaning lost or changed"],
  ["not_equivalent", "Not equivalent"],
  ["unsure", "Unsure"],
] as const;
const SAFETY = [
  ["safe", "Safe"],
  ["unsafe", "Unsafe"],
  ["unsure", "Unsure"],
] as const;
const field = "min-w-0 rounded-md border border-line bg-surface-2 px-2 py-1 text-sm";

function RadioGroup({ name, legend, options, value, onChange }: {
  name: string; legend: string; options: readonly (readonly [string, string])[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1 text-xs font-medium text-muted">{legend}</legend>
      {options.map(([v, label]) => (
        <label key={v} className="flex items-center gap-2 text-sm">
          <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} />
          {label}
        </label>
      ))}
    </fieldset>
  );
}

function AnnotatePanel({ annotator }: { annotator: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [semantic, setSemantic] = useState("");
  const [safety, setSafety] = useState("");
  const [note, setNote] = useState("");
  const item = useQuery({ queryKey: ["queue", annotator], queryFn: () => api.queue(annotator) });
  const submit = useMutation<unknown, ApiError, number>({
    mutationFn: (taskId) => api.annotate(taskId, { annotator, semantic_label: semantic, safety_label: safety, note }),
    onSuccess: () => {
      setSemantic(""); setSafety(""); setNote("");
      toast("Annotation saved");
      void qc.invalidateQueries({ queryKey: ["queue", annotator] });
      void qc.invalidateQueries({ queryKey: ["agreement"] });
      void qc.invalidateQueries({ queryKey: ["disagreements"] });
      void qc.invalidateQueries({ queryKey: ["annotators"] });
    },
  });
  if (item.isPending) return <p className="p-4 text-sm text-muted">Loading queue…</p>;
  if (item.isError) return <p role="alert" className="p-4 text-sm text-red-500">{item.error.message}</p>;
  const it = item.data;
  if (!it) return <p className="p-4 text-sm text-muted" data-testid="queue-empty">Your queue is empty. Thank you!</p>;
  return (
    <form className="flex flex-col gap-4 p-4" aria-label="Annotation form" aria-busy={submit.isPending} onSubmit={(e: FormEvent) => { e.preventDefault(); submit.mutate(it.task_id); }}>
      <p className="flex flex-wrap gap-2 text-xs text-muted">
        <span data-testid="queue-task"><Badge>task {it.task_id}</Badge></span><Badge tone="cyan">{it.language}</Badge><Badge>guideline {it.guideline_version}</Badge>
        <span>{it.remaining} remaining</span>
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div><p className="mb-1 text-xs text-muted">Source</p><p className="rounded-md bg-surface-2 p-3 text-lg break-words" data-testid="queue-source">{it.source_text}</p></div>
        <div><p className="mb-1 text-xs text-muted">Variant</p><p className="rounded-md bg-surface-2 p-3 text-lg break-words" data-testid="queue-variant">{it.variant_text}</p></div>
      </div>
      <fieldset disabled={submit.isPending} className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <RadioGroup name="semantic" legend="Does the variant mean the same as the source?" options={SEMANTIC} value={semantic} onChange={setSemantic} />
        <RadioGroup name="safety" legend="Safety (under the guideline's synthetic policy)" options={SAFETY} value={safety} onChange={setSafety} />
      </fieldset>
      <label className="flex flex-col gap-1 text-xs text-muted">Note (optional)
        <textarea rows={2} maxLength={2000} className={field} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      {submit.isError && <p role="alert" className="text-xs text-red-500">{submit.error.code}: {submit.error.message}</p>}
      <Button type="submit" variant="primary" disabled={!semantic || !safety || submit.isPending} className="w-fit">
        <ClipboardCheck className="size-3.5" /> Submit and next
      </Button>
    </form>
  );
}

function SetupPanel() {
  const qc = useQueryClient();
  const toast = useToast();
  const [g, setG] = useState({ version: "", title: "", body: "" });
  const [t, setT] = useState({ dataset: "", version: 1, recipe_hash: "", guideline_version: "", per_language: 30 });
  const guidelines = useQuery({ queryKey: ["guidelines"], queryFn: api.guidelines });
  const newG = useMutation<unknown, ApiError, void>({
    mutationFn: () => api.createGuideline(g),
    onSuccess: () => { toast(`Guideline ${g.version} saved`); void qc.invalidateQueries({ queryKey: ["guidelines"] }); },
  });
  const newT = useMutation<{ created: number; existing: number }, ApiError, void>({
    mutationFn: () => api.createTasks(t),
    onSuccess: (r) => { toast(`Created ${r.created} tasks (${r.existing} existed)`); void qc.invalidateQueries({ queryKey: ["queue"] }); },
  });
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader title="Guidelines (immutable versions)" />
        <div className="flex flex-col gap-3 p-4">
          {guidelines.data?.length ? (
            <ul className="flex flex-col gap-2 text-sm">
              {guidelines.data.map((x) => (
                <li key={x.version}><details><summary className="cursor-pointer"><span className="font-mono text-xs">{x.version}</span> {x.title}</summary><p className="mt-1 text-xs whitespace-pre-wrap text-muted">{x.body}</p></details></li>
              ))}
            </ul>
          ) : <p className="text-xs text-muted">No guidelines yet.</p>}
          <form className="flex flex-col gap-2" aria-label="New guideline" onSubmit={(e) => { e.preventDefault(); newG.mutate(); }}>
            <div className="flex gap-2">
              <input aria-label="Guideline version" required placeholder="version e.g. v1" className={`${field} w-28 shrink-0 font-mono`} value={g.version} onChange={(e) => setG({ ...g, version: e.target.value })} />
              <input aria-label="Guideline title" required placeholder="title" className={`${field} flex-1`} value={g.title} onChange={(e) => setG({ ...g, title: e.target.value })} />
            </div>
            <textarea aria-label="Guideline body" required rows={3} placeholder="Instructions shown to annotators" className={field} value={g.body} onChange={(e) => setG({ ...g, body: e.target.value })} />
            {newG.isError && <p role="alert" className="text-xs text-red-500">{newG.error.message}</p>}
            <Button type="submit" className="w-fit">Save guideline version</Button>
          </form>
        </div>
      </Card>
      <Card>
        <CardHeader title="Create annotation tasks" />
        <form className="grid grid-cols-2 gap-2 p-4" aria-label="New tasks" onSubmit={(e) => { e.preventDefault(); newT.mutate(); }}>
          <label className="flex flex-col gap-1 text-xs text-muted">Dataset slug<input required className={field} value={t.dataset} onChange={(e) => setT({ ...t, dataset: e.target.value })} /></label>
          <label className="flex flex-col gap-1 text-xs text-muted">Version<input required type="number" min={1} className={field} value={t.version} onChange={(e) => setT({ ...t, version: Number(e.target.value) })} /></label>
          <label className="col-span-2 flex flex-col gap-1 text-xs text-muted">Variant recipe hash<input required minLength={64} maxLength={64} className={`${field} font-mono text-xs`} value={t.recipe_hash} onChange={(e) => setT({ ...t, recipe_hash: e.target.value })} /></label>
          <label className="flex flex-col gap-1 text-xs text-muted">Guideline version<input required className={field} value={t.guideline_version} onChange={(e) => setT({ ...t, guideline_version: e.target.value })} /></label>
          <label className="flex flex-col gap-1 text-xs text-muted">Per language<input required type="number" min={1} max={1000} className={field} value={t.per_language} onChange={(e) => setT({ ...t, per_language: Number(e.target.value) })} /></label>
          {newT.isError && <p role="alert" className="col-span-2 text-xs text-red-500">{newT.error.code}: {newT.error.message}</p>}
          <Button type="submit" className="col-span-2 w-fit">Create stratified tasks</Button>
        </form>
      </Card>
    </div>
  );
}

function ReviewPanel() {
  const qc = useQueryClient();
  const agreement = useQuery({ queryKey: ["agreement"], queryFn: api.agreement });
  const dis = useQuery({ queryKey: ["disagreements"], queryFn: api.disagreements });
  const [adj, setAdj] = useState<Record<number, { semantic: string; safety: string; rationale: string }>>({});
  const adjudicate = useMutation<unknown, ApiError, number>({
    mutationFn: (id) => api.adjudicate(id, { adjudicator: "adjudicator", semantic_label: adj[id]?.semantic ?? "", safety_label: adj[id]?.safety ?? "", rationale: adj[id]?.rationale ?? "" }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["disagreements"] }); void qc.invalidateQueries({ queryKey: ["agreement"] }); },
  });
  const a = agreement.data;
  const fmt = (x: number | null) => (x === null ? "undefined" : x.toFixed(3));
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader title="Agreement (semantic labels)" />
        {a && (
          <div className="flex flex-col gap-3 p-4 text-sm">
            <dl className="grid grid-cols-3 gap-3">
              <div><dt className="text-xs text-muted">Annotations</dt><dd className="font-mono">{a.annotations}</dd></div>
              <div><dt className="text-xs text-muted">Multi-rated tasks</dt><dd className="font-mono">{a.tasks_with_two_or_more}</dd></div>
              <div><dt className="text-xs text-muted">Krippendorff alpha</dt><dd className="font-mono" data-testid="alpha">{fmt(a.alpha_nominal)}</dd></div>
            </dl>
            {a.pairwise_kappa.map((p) => (
              <p key={p.annotators.join()} className="font-mono text-xs">kappa({p.annotators[0]}, {p.annotators[1]}) = {fmt(p.kappa)} over {p.items} items</p>
            ))}
            <Distribution title="Label counts" data={a.label_counts} />
            <p className="text-xs text-muted">{a.note} “unsure” is treated as missing. Adjudicated: {a.adjudicated}.</p>
          </div>
        )}
      </Card>
      <Card>
        <CardHeader title={`Disagreements (${dis.data?.length ?? 0})`} />
        {dis.data?.length === 0 ? <p className="p-4 text-sm text-muted">No open disagreements.</p> : (
          <ul className="divide-y divide-line" aria-label="Disagreements">
            {dis.data?.map((d) => (
              <li key={d.task_id} className="flex flex-col gap-2 p-4 text-sm">
                <p><span className="text-muted">source:</span> {d.source_text}<br /><span className="text-muted">variant:</span> {d.variant_text}</p>
                <p className="flex flex-wrap gap-1">{d.labels.map((l) => <Badge key={l.annotator}>{l.annotator}: {l.semantic_label}</Badge>)}</p>
                <form className="flex flex-wrap items-end gap-2" aria-label={`Adjudicate task ${d.task_id}`} onSubmit={(e) => { e.preventDefault(); adjudicate.mutate(d.task_id); }}>
                  <select aria-label="Adjudicated label" required className={field} value={adj[d.task_id]?.semantic ?? ""} onChange={(e) => setAdj({ ...adj, [d.task_id]: { safety: "", rationale: "", ...adj[d.task_id], semantic: e.target.value } })}>
                    <option value="">label…</option>{SEMANTIC.map(([v]) => <option key={v}>{v}</option>)}
                  </select>
                  <select aria-label="Adjudicated safety" required className={field} value={adj[d.task_id]?.safety ?? ""} onChange={(e) => setAdj({ ...adj, [d.task_id]: { semantic: "", rationale: "", ...adj[d.task_id], safety: e.target.value } })}>
                    <option value="">safety…</option>{SAFETY.map(([v]) => <option key={v}>{v}</option>)}
                  </select>
                  <input aria-label="Rationale" required placeholder="rationale" className={`${field} flex-1`} value={adj[d.task_id]?.rationale ?? ""} onChange={(e) => setAdj({ ...adj, [d.task_id]: { semantic: "", safety: "", ...adj[d.task_id], rationale: e.target.value } })} />
                  <Button type="submit">Adjudicate</Button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export function AnnotationStudio() {
  const qc = useQueryClient();
  const annotators = useQuery({ queryKey: ["annotators"], queryFn: api.annotators });
  const [who, setWho] = useState("");
  const [reg, setReg] = useState<{ pseudonym: string; proficiency: Record<string, string> }>({ pseudonym: "", proficiency: Object.fromEntries(VARIETIES.map((v) => [v, "none"])) });
  const create = useMutation<unknown, ApiError, void>({
    mutationFn: () => api.createAnnotator(reg),
    onSuccess: () => { setWho(reg.pseudonym); void qc.invalidateQueries({ queryKey: ["annotators"] }); },
  });
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Annotation Studio</h1>
        <p className="mt-1 text-sm text-muted">
          Blinded, independent human judgments of semantic equivalence and safety. Every label here is entered by a
          person; nothing is generated or imputed.
        </p>
      </div>
      <Card>
        <CardHeader title="Annotator" />
        <div className="flex flex-wrap items-end gap-6 p-4">
          <label className="flex flex-col gap-1 text-xs text-muted">Annotate as
            <select className={field} value={who} onChange={(e) => setWho(e.target.value)}>
              <option value="">Select…</option>
              {annotators.data?.map((a) => <option key={a.pseudonym} value={a.pseudonym}>{a.pseudonym} ({a.annotations})</option>)}
            </select>
          </label>
          <form className="flex flex-wrap items-end gap-2" aria-label="Register annotator" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
            <label className="flex flex-col gap-1 text-xs text-muted">New pseudonym
              <input required pattern="[A-Za-z0-9_-]{2,64}" className={`${field} w-36`} value={reg.pseudonym} onChange={(e) => setReg({ ...reg, pseudonym: e.target.value })} />
            </label>
            {VARIETIES.map((v) => (
              <label key={v} className="flex flex-col gap-1 text-xs text-muted">{v}
                <select aria-label={`Proficiency ${v}`} className={field} value={reg.proficiency[v]} onChange={(e) => setReg({ ...reg, proficiency: { ...reg.proficiency, [v]: e.target.value } })}>
                  {["none", "basic", "fluent", "native"].map((l) => <option key={l}>{l}</option>)}
                </select>
              </label>
            ))}
            <Button type="submit"><UserPlus className="size-3.5" /> Register</Button>
          </form>
          {create.isError && <p role="alert" className="text-xs text-red-500">{create.error.message}</p>}
        </div>
      </Card>
      <Card>
        <CardHeader title="Annotate" />
        {who ? <AnnotatePanel key={who} annotator={who} /> : <p className="p-4 text-sm text-muted">Select or register an annotator to start.</p>}
      </Card>
      <ReviewPanel />
      <SetupPanel />
    </div>
  );
}
