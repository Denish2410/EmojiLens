import type {
  ExperimentRow,
  InferResult,
  ModelsInfo,
  OutputRow,
  RecipeRow,
  AgreementStats,
  AnnotatorRow,
  DisagreementRow,
  GuidelineRow,
  QueueItem,
  ApiErrorBody,
  ApplyResult,
  ChainStepIn,
  GenerateResult,
  TransformSpec,
  Dataset,
  DatasetKind,
  Health,
  ImportResult,
  MultilingualResult,
  Readiness,
  SourcePage,
  UnicodeAnalysis,
  VarietyInfo,
  VersionDetail,
} from "./types";

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isErrorBody(x: unknown): x is ApiErrorBody {
  return (
    typeof x === "object" &&
    x !== null &&
    "error" in x &&
    typeof (x as ApiErrorBody).error?.code === "string"
  );
}

async function request<T>(path: string, init?: RequestInit, allow?: number[]): Promise<T> {
  let res: Response;
  try {
    res = await fetch(new URL(`${API_BASE}${path}`, window.location.origin), {
      ...init,
      headers: { "Content-Type": "application/json", ...((init?.headers as Record<string, string>) ?? {}) },
    });
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the EmojiLens API.");
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok && !allow?.includes(res.status)) {
    if (isErrorBody(body)) {
      throw new ApiError(res.status, body.error.code, body.error.message, body.error.details);
    }
    throw new ApiError(res.status, "http_error", `Request failed with status ${res.status}.`);
  }
  return body as T;
}

export const api = {
  health: () => request<Health>("/health"),
  ready: () => request<Readiness>("/ready", undefined, [503]),
  analyzeUnicode: (text: string) =>
    request<UnicodeAnalysis>("/unicode/analyze", {
      method: "POST",
      // JSON.stringify preserves every code point; lone surrogates are escaped as \uD8xx
      // and rejected server-side with invalid_unicode.
      body: JSON.stringify({ text }),
    }),
  multilingual: (text: string) =>
    request<MultilingualResult>("/multilingual/analyze", { method: "POST", body: JSON.stringify({ text }) }),
  varieties: () => request<VarietyInfo[]>("/multilingual/varieties"),
  transforms: () => request<TransformSpec[]>("/transforms"),
  models: () => request<ModelsInfo>("/models"),
  infer: (key: string, capability: string, text: string) =>
    request<InferResult>(`/models/${encodeURIComponent(key)}/infer`, {
      method: "POST",
      body: JSON.stringify({ capability, text }),
    }),
  recipes: (slug: string, n: number) =>
    request<RecipeRow[]>(`/datasets/${encodeURIComponent(slug)}/versions/${n}/recipes`),
  experiments: () => request<ExperimentRow[]>("/experiments"),
  experiment: (id: number) => request<ExperimentRow>(`/experiments/${id}`),
  createExperiment: (body: Record<string, unknown>) =>
    request<ExperimentRow>("/experiments", { method: "POST", body: JSON.stringify(body) }),
  cancelExperiment: (id: number) => request<ExperimentRow>(`/experiments/${id}/cancel`, { method: "POST" }),
  resumeExperiment: (id: number) => request<ExperimentRow>(`/experiments/${id}/resume`, { method: "POST" }),
  outputs: (id: number, params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "" && v !== false) qs.set(k, String(v));
    return request<{ total: number; page: number; page_size: number; items: OutputRow[] }>(`/experiments/${id}/outputs?${qs}`);
  },
  annotators: () => request<AnnotatorRow[]>("/annotation/annotators"),
  createAnnotator: (body: { pseudonym: string; proficiency: Record<string, string> }) =>
    request<AnnotatorRow>("/annotation/annotators", { method: "POST", body: JSON.stringify(body) }),
  guidelines: () => request<GuidelineRow[]>("/annotation/guidelines"),
  createGuideline: (body: GuidelineRow) =>
    request<GuidelineRow>("/annotation/guidelines", { method: "POST", body: JSON.stringify(body) }),
  createTasks: (body: { dataset: string; version: number; recipe_hash: string; guideline_version: string; per_language: number }) =>
    request<{ created: number; existing: number; by_language: Record<string, number> }>("/annotation/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  queue: (annotator: string) =>
    request<QueueItem | null>(`/annotation/queue?annotator=${encodeURIComponent(annotator)}`),
  annotate: (taskId: number, body: { annotator: string; semantic_label: string; safety_label: string; note: string }) =>
    request<{ task_id: number }>(`/annotation/tasks/${taskId}/annotations`, { method: "POST", body: JSON.stringify(body) }),
  disagreements: () => request<DisagreementRow[]>("/annotation/disagreements"),
  adjudicate: (taskId: number, body: { adjudicator: string; semantic_label: string; safety_label: string; rationale: string }) =>
    request<{ task_id: number }>(`/annotation/tasks/${taskId}/adjudication`, { method: "POST", body: JSON.stringify(body) }),
  agreement: () => request<AgreementStats>("/annotation/agreement"),
  applyChain: (body: { text: string; variety: string; seed: number; chain: ChainStepIn[] }) =>
    request<ApplyResult>("/transforms/apply", { method: "POST", body: JSON.stringify(body) }),
  generateVariants: (slug: string, n: number, body: { seed: number; chain: ChainStepIn[] }) =>
    request<GenerateResult>(`/datasets/${encodeURIComponent(slug)}/versions/${n}/variants`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  datasets: () => request<Dataset[]>("/datasets"),
  dataset: (slug: string) => request<Dataset>(`/datasets/${encodeURIComponent(slug)}`),
  createDataset: (body: { slug: string; name: string; description: string; kind: DatasetKind; license: string }) =>
    request<Dataset>("/datasets", { method: "POST", body: JSON.stringify(body) }),
  importVersion: (slug: string, file: Blob) =>
    request<ImportResult>(`/datasets/${encodeURIComponent(slug)}/versions`, {
      method: "POST",
      body: file,
      headers: { "Content-Type": "application/x-ndjson" },
    }),
  version: (slug: string, n: number) =>
    request<VersionDetail>(`/datasets/${encodeURIComponent(slug)}/versions/${n}`),
  freeze: (slug: string, n: number, seed: number) =>
    request<VersionDetail>(`/datasets/${encodeURIComponent(slug)}/versions/${n}/freeze`, {
      method: "POST",
      body: JSON.stringify({ seed }),
    }),
  sources: (slug: string, n: number, params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, String(v));
    return request<SourcePage>(`/datasets/${encodeURIComponent(slug)}/versions/${n}/sources?${qs}`);
  },
};
