import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Database, FlaskConical, Lock, Plus, Upload } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError, api } from "../api/client";
import type { Dataset, DatasetKind, ImportResult } from "../api/types";
import { Distribution } from "../components/Distribution";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";

function KindBadge({ kind }: { kind: DatasetKind }) {
  return kind === "synthetic_fixture" ? (
    <Badge tone="amber" title="Excluded from research results">synthetic fixture</Badge>
  ) : (
    <Badge tone="cyan">evaluation</Badge>
  );
}

function NewDatasetForm({ onDone }: { onDone: (slug: string) => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ slug: "", name: "", description: "", kind: "evaluation" as DatasetKind, license: "" });
  const create = useMutation({
    mutationFn: api.createDataset,
    onSuccess: (ds) => {
      void qc.invalidateQueries({ queryKey: ["datasets"] });
      onDone(ds.slug);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(form);
  };
  const field = "w-full rounded-md border border-line bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-violet-500";
  return (
    <form onSubmit={submit} className="flex flex-col gap-3 p-4" aria-label="New dataset">
      <label className="flex flex-col gap-1 text-xs text-muted">
        Slug
        <input required pattern="[a-z0-9][a-z0-9-]*" minLength={2} maxLength={64} className={field}
          value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Name
        <input required maxLength={200} className={field} value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Description
        <textarea rows={2} maxLength={4000} className={field} value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Kind
          <select className={field} value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value as DatasetKind })}>
            <option value="evaluation">evaluation</option>
            <option value="synthetic_fixture">synthetic fixture</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          License
          <input required maxLength={128} className={field} value={form.license} placeholder="e.g. CC-BY-4.0"
            onChange={(e) => setForm({ ...form, license: e.target.value })} />
        </label>
      </div>
      {create.isError && (
        <p role="alert" className="text-xs text-red-500">
          {(create.error as ApiError).code}: {create.error.message}
        </p>
      )}
      <Button type="submit" variant="primary" disabled={create.isPending}>
        {create.isPending ? "Creating…" : "Create dataset"}
      </Button>
    </form>
  );
}

function ImportPanel({ ds, onImported }: { ds: Dataset; onImported: (r: ImportResult) => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const imp = useMutation<ImportResult, ApiError, File>({
    mutationFn: (file) => api.importVersion(ds.slug, file),
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: ["dataset", ds.slug] });
      void qc.invalidateQueries({ queryKey: ["datasets"] });
      toast(`Imported version ${r.version.number} (${r.version.record_count} records)`);
      onImported(r);
    },
  });
  const lineErrors =
    imp.error?.code === "dataset_validation_failed"
      ? ((imp.error.details as { errors?: { line: number; code: string; message: string }[] })?.errors ?? [])
      : [];
  return (
    <div className="flex flex-col gap-2">
      <label className="inline-flex w-fit cursor-pointer items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-surface-2 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-violet-500">
        <Upload className="size-3.5" />
        {imp.isPending ? "Importing…" : "Import JSONL as new version"}
        <input
          type="file"
          accept=".jsonl,.ndjson,application/x-ndjson"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) imp.mutate(f);
            e.target.value = "";
          }}
        />
      </label>
      {imp.isError && (
        <div role="alert" className="rounded-md border border-red-500/30 bg-red-500/5 p-3 text-xs">
          <p className="font-medium text-red-500">
            {imp.error.code}: {imp.error.message}
          </p>
          {lineErrors.length > 0 && (
            <ul className="mt-2 max-h-48 overflow-auto font-mono">
              {lineErrors.map((e) => (
                <li key={`${e.line}-${e.code}`}>
                  line {e.line} · {e.code} · {e.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {imp.data && imp.data.duplicates.length > 0 && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs">
          <p className="font-medium">Duplicates detected in this upload</p>
          <ul className="mt-1 font-mono">
            {imp.data.duplicates.map((d) => (
              <li key={d.ids.join()}>
                {d.kind}: {d.ids.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function VersionPanel({ slug, n }: { slug: string; n: number }) {
  const qc = useQueryClient();
  const [seed, setSeed] = useState("20261124");
  const [filters, setFilters] = useState({ language: "", split: "", safety_label: "", control: "", q: "" });
  const [page, setPage] = useState(1);
  const detail = useQuery({ queryKey: ["version", slug, n], queryFn: () => api.version(slug, n) });
  const sources = useQuery({
    queryKey: ["sources", slug, n, filters, page],
    queryFn: () => api.sources(slug, n, { ...filters, page, page_size: 25 }),
  });
  const freeze = useMutation<unknown, ApiError, number>({
    mutationFn: (s) => api.freeze(slug, n, s),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["version", slug, n] });
      void qc.invalidateQueries({ queryKey: ["sources", slug, n] });
      void qc.invalidateQueries({ queryKey: ["dataset", slug] });
    },
  });

  if (detail.isPending) return <Skeleton className="h-40 w-full" />;
  if (detail.isError) return <p role="alert" className="text-sm text-red-500">{detail.error.message}</p>;
  const d = detail.data;
  const v = d.version;
  const pages = sources.data ? Math.max(1, Math.ceil(sources.data.total / sources.data.page_size)) : 1;
  const select = "rounded-md border border-line bg-surface-2 px-2 py-1 text-xs";

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader
          title={`Version ${v.number}`}
          actions={v.frozen_at ? <Badge tone="emerald"><Lock className="mr-1 size-3" />frozen</Badge> : <Badge>not frozen</Badge>}
        />
        <dl className="grid gap-3 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="text-xs text-muted">Records</dt><dd className="font-mono">{v.record_count}</dd></div>
          <div><dt className="text-xs text-muted">Schema</dt><dd className="font-mono">v{v.schema_version}</dd></div>
          <div><dt className="text-xs text-muted">Split method</dt><dd className="font-mono text-xs">{v.split_method ?? "—"}</dd></div>
          <div><dt className="text-xs text-muted">Seed · ratios</dt><dd className="font-mono text-xs">{v.split_seed ?? "—"} · {v.split_ratios?.join(" / ") ?? "—"}</dd></div>
          <div className="sm:col-span-2 lg:col-span-4">
            <dt className="text-xs text-muted">Content SHA-256</dt>
            <dd className="font-mono text-xs break-all" data-testid="content-hash">{v.content_sha256}</dd>
          </div>
        </dl>
        {!v.frozen_at && (
          <form
            className="flex flex-wrap items-end gap-2 border-t border-line px-4 py-3"
            onSubmit={(e) => {
              e.preventDefault();
              freeze.mutate(Number(seed));
            }}
          >
            <label className="flex flex-col gap-1 text-xs text-muted">
              Split seed
              <input type="number" min={0} required value={seed} onChange={(e) => setSeed(e.target.value)}
                className="w-36 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-sm" />
            </label>
            <Button type="submit" variant="primary" disabled={freeze.isPending}>
              <Lock className="size-3.5" /> Freeze splits (70/15/15 by source group)
            </Button>
            {freeze.isError && <span role="alert" className="text-xs text-red-500">{freeze.error.message}</span>}
          </form>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Distributions" />
          <div className="grid gap-5 p-4 sm:grid-cols-2">
            <Distribution title="Language" data={d.stats.language} />
            <Distribution title="Split" data={d.stats.split} tone="cyan" />
            <Distribution title="Safety label" data={d.stats.safety_label} />
            <Distribution title="Control type" data={d.stats.control} tone="cyan" />
          </div>
        </Card>
        <Card>
          <CardHeader title="Integrity and leakage" />
          <div className="flex flex-col gap-3 p-4 text-sm">
            {!d.leakage_checked ? (
              <p className="text-muted">Leakage is validated when the version is frozen and splits are assigned.</p>
            ) : d.leakage.length === 0 ? (
              <p className="text-emerald-600 dark:text-emerald-400" data-testid="leakage-ok">
                No leakage: every source group sits in one split and no text (exact or normalized) crosses splits.
              </p>
            ) : (
              <ul className="flex flex-col gap-1 font-mono text-xs text-red-500" data-testid="leakage-issues">
                {d.leakage.map((i) => (
                  <li key={`${i.kind}-${i.ids.join()}`}>
                    {i.kind}: {i.ids.join(", ")} ({i.splits.join(" / ")})
                  </li>
                ))}
              </ul>
            )}
            <div>
              <p className="text-xs text-muted">Declared language vs. heuristic identification</p>
              <p className="font-mono text-xs">
                agree {d.language_agreement.agree} · disagree {d.language_agreement.disagree} · undetected{" "}
                {d.language_agreement.undetected}
              </p>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Sources" actions={<span className="font-mono text-xs text-muted">{sources.data?.total ?? 0} matching</span>} />
        <div className="flex flex-wrap gap-2 border-b border-line px-4 py-3">
          <input aria-label="Search text" placeholder="Search text…" value={filters.q} maxLength={200}
            onChange={(e) => { setPage(1); setFilters({ ...filters, q: e.target.value }); }}
            className="min-w-40 flex-1 rounded-md border border-line bg-surface-2 px-2 py-1 text-sm" />
          {(
            [
              ["language", ["en", "hi", "gu", "hi-Latn", "gu-Latn"]],
              ["split", ["train", "validation", "test"]],
              ["safety_label", ["safe", "unsafe", "unknown"]],
              ["control", ["clean", "heavy_emoji", "indic_joiner", "code_mixed", "identity", "decoration"]],
            ] as const
          ).map(([key, opts]) => (
            <select key={key} aria-label={`Filter by ${key}`} className={select} value={filters[key]}
              onChange={(e) => { setPage(1); setFilters({ ...filters, [key]: e.target.value }); }}>
              <option value="">{key}: all</option>
              {opts.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-line">
                {["ID", "Text", "Lang (detected)", "Group", "Split", "Label", "Control"].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sources.data?.items.map((s) => (
                <tr key={s.external_id} className="border-b border-line/60 align-top">
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{s.external_id}</td>
                  <td className="max-w-md px-3 py-2 break-words">{s.text}</td>
                  <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">
                    {s.language}{" "}
                    <span className={clsx(s.detected_language !== s.language && "text-amber-600 dark:text-amber-300")}>
                      ({s.detected_language ?? "?"})
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{s.source_group}</td>
                  <td className="px-3 py-2 font-mono text-xs">{s.split ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{s.safety_label}</td>
                  <td className="px-3 py-2 font-mono text-xs">{s.control ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {sources.data?.items.length === 0 && <p className="p-4 text-sm text-muted">No sources match these filters.</p>}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-line px-4 py-2 text-xs">
          <Button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>Previous</Button>
          <span className="font-mono">page {page} / {pages}</span>
          <Button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>Next</Button>
        </div>
      </Card>
    </div>
  );
}

export function DatasetExplorer() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const list = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const ds = useQuery({ queryKey: ["dataset", slug], queryFn: () => api.dataset(slug ?? ""), enabled: Boolean(slug) });
  const versions = ds.data?.versions ?? [];
  const current = selectedVersion ?? versions.at(-1)?.number ?? null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dataset Explorer</h1>
          <p className="mt-1 text-sm text-muted">
            Versioned, hashed source datasets with group-aware frozen splits and leakage validation.
          </p>
        </div>
        <Button variant="primary" onClick={() => setCreating((c) => !c)} aria-expanded={creating}>
          <Plus className="size-3.5" /> New dataset
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
        <div className="flex flex-col gap-4">
          {creating && (
            <Card>
              <CardHeader title="New dataset" />
              <NewDatasetForm onDone={(s) => { setCreating(false); navigate(`/datasets/${s}`); }} />
            </Card>
          )}
          <Card>
            <CardHeader title="Datasets" />
            {list.isPending ? (
              <div className="p-4"><Skeleton className="h-16 w-full" /></div>
            ) : list.isError ? (
              <p role="alert" className="p-4 text-sm text-red-500">{list.error.message}</p>
            ) : list.data.length === 0 ? (
              <div className="flex flex-col items-start gap-2 p-4 text-sm text-muted">
                <Database className="size-5" />
                <p>No datasets yet. Create one, then import a JSONL file (schema v1).</p>
              </div>
            ) : (
              <ul className="divide-y divide-line" aria-label="Datasets">
                {list.data.map((d) => (
                  <li key={d.slug}>
                    <Link
                      to={`/datasets/${d.slug}`}
                      onClick={() => setSelectedVersion(null)}
                      aria-current={d.slug === slug ? "page" : undefined}
                      className={clsx("flex flex-col gap-1 px-4 py-3 hover:bg-surface-2", d.slug === slug && "bg-violet-500/10")}
                    >
                      <span className="text-sm font-medium">{d.name}</span>
                      <span className="flex items-center gap-2">
                        <KindBadge kind={d.kind} />
                        <span className="font-mono text-[11px] text-muted">{d.versions.length} version(s)</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="min-w-0">
          {!slug ? (
            <Card className="flex flex-col items-center gap-2 p-10 text-center text-sm text-muted">
              <FlaskConical className="size-6" />
              Select a dataset to inspect its versions, splits and sources.
            </Card>
          ) : ds.isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : ds.isError ? (
            <p role="alert" className="text-sm text-red-500">{ds.error.message}</p>
          ) : (
            <div className="flex flex-col gap-6">
              <Card>
                <div className="flex flex-col gap-3 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold">{ds.data.name}</h2>
                    <KindBadge kind={ds.data.kind} />
                    <Badge>{ds.data.license}</Badge>
                  </div>
                  {ds.data.description && <p className="text-sm text-muted">{ds.data.description}</p>}
                  {ds.data.kind === "synthetic_fixture" && (
                    <p className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs">
                      Synthetic development fixture: excluded from every reported research result.
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-3">
                    <ImportPanel ds={ds.data} onImported={(r) => setSelectedVersion(r.version.number)} />
                    {versions.length > 0 && (
                      <label className="flex items-center gap-2 text-xs text-muted">
                        Version
                        <select className="rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-xs"
                          value={current ?? ""} onChange={(e) => setSelectedVersion(Number(e.target.value))}>
                          {versions.map((v) => (
                            <option key={v.number} value={v.number}>v{v.number} · {v.record_count} records{v.frozen_at ? " · frozen" : ""}</option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                </div>
              </Card>
              {current !== null ? (
                <VersionPanel key={`${slug}-${current}`} slug={ds.data.slug} n={current} />
              ) : (
                <Card className="p-6 text-sm text-muted">No versions yet. Import a JSONL file to create version 1.</Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
