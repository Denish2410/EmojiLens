// Mirrors apps/api/src/emojilens_api/schemas.py (v1). Keep in sync.

export interface Span {
  cp_start: number;
  cp_end: number;
  utf8_start: number;
  utf8_end: number;
  utf16_start: number;
  utf16_end: number;
}

export type CodepointKind =
  | "zero_width"
  | "joiner"
  | "variation_selector"
  | "tag"
  | "bidi_control"
  | "filler"
  | "format"
  | "control"
  | "emoji_modifier"
  | "regional_indicator"
  | "combining_enclosing_keycap";

export interface Codepoint {
  index: number;
  char: string;
  codepoint: string;
  name: string;
  category: string;
  bidi_class: string;
  combining_class: number;
  utf8_hex: string;
  span: Span;
  kinds: CodepointKind[];
  invisible: boolean;
}

export interface Grapheme {
  index: number;
  text: string;
  span: Span;
  codepoint_count: number;
}

export interface UnicodeAnalysis {
  original: string;
  sha256: string;
  lengths: { codepoints: number; graphemes: number; utf8_bytes: number; utf16_units: number };
  normalization: { is_nfc: boolean; is_nfd: boolean; is_nfkc: boolean; is_nfkd: boolean };
  graphemes: Grapheme[];
  codepoints: Codepoint[];
  invisible_count: number;
  scripts: { counts: Record<string, number>; dominant: string | null; is_mixed: boolean };
  evidence: Evidence[];
  views: DerivedView[];
  engine: {
    engine_version: string;
    ruleset_version: string;
    unicodedata_version: string;
    regex_version: string;
    emoji_version: string;
  };
}

export type EvidenceCategory =
  | "legitimate_structure"
  | "informational"
  | "anomalous"
  | "suspicious"
  | "concealed_payload_decoded";

export const EVIDENCE_ORDER: EvidenceCategory[] = [
  "legitimate_structure",
  "informational",
  "anomalous",
  "suspicious",
  "concealed_payload_decoded",
];

export interface Evidence {
  id: string;
  rule: string;
  category: EvidenceCategory;
  message: string;
  span: Span;
  details: Record<string, unknown>;
}

export type ViewName = "original" | "nfc" | "nfkc" | "sanitized" | "demojized" | "decoded";

export interface ViewSegment {
  original: Span;
  view: Span;
  text: string;
}

export interface DerivedView {
  name: ViewName;
  description: string;
  text: string;
  changed: boolean;
  segments: ViewSegment[];
}

export interface Health {
  status: "ok";
  version: string;
}

export interface Readiness {
  status: "ready" | "not_ready";
  checks: { name: string; ok: boolean; detail: string }[];
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}

// ---- Datasets (v1) ----
export type DatasetKind = "evaluation" | "synthetic_fixture";

export interface DatasetVersion {
  number: number;
  content_sha256: string;
  record_count: number;
  schema_version: number;
  split_seed: number | null;
  split_ratios: number[] | null;
  split_method: string | null;
  frozen_at: string | null;
  created_at: string;
}

export interface Dataset {
  slug: string;
  name: string;
  description: string;
  kind: DatasetKind;
  license: string;
  created_at: string;
  versions: DatasetVersion[];
}

export interface LeakageIssue {
  kind: string;
  ids: string[];
  splits: string[];
}

export interface VersionDetail {
  dataset: string;
  version: DatasetVersion;
  stats: Record<"language" | "split" | "safety_label" | "control", Record<string, number>>;
  language_agreement: { agree: number; disagree: number; undetected: number };
  leakage: LeakageIssue[];
  leakage_checked: boolean;
}

export interface SourceRow {
  external_id: string;
  source_group: string;
  text: string;
  text_sha256: string;
  language: string;
  detected_language: string | null;
  detected_confidence: number | null;
  safety_label: string;
  control: string | null;
  origin: string;
  license: string;
  meta: Record<string, unknown>;
  split: string | null;
}

export interface SourcePage {
  total: number;
  page: number;
  page_size: number;
  items: SourceRow[];
}

export interface ImportResult {
  dataset: string;
  version: DatasetVersion;
  duplicates: { kind: string; ids: string[] }[];
}

// ---- Multilingual (v1) ----
export interface MultilingualResult {
  identification: {
    label: string | null;
    confidence: number;
    uncertain: boolean;
    reasons: string[];
    scores: Record<string, number>;
    code_mixed: boolean;
    cmi: number;
    switch_points: number;
    method: string;
  };
  tokens: { text: string; cp_start: number; cp_end: number; tag: string; candidates: string[] }[];
  scripts: Record<string, number>;
  dominant_script: string | null;
  emoji: {
    emoji: string;
    cp_start: number;
    cp_end: number;
    meanings: { variety: string; locale: string; name: string; keywords: string[]; fallback: boolean }[];
  }[];
  cldr_version: string;
}

export interface VarietyInfo {
  code: string;
  name: string;
  script: string;
  cldr_locale: string | null;
  notes: string;
}

// ---- Transforms (v1) ----
export interface TransformParam {
  name: string;
  kind: "float" | "int" | "choice" | "string" | "bool";
  default: unknown;
  description: string;
  choices: string[];
  minimum: number | null;
  maximum: number | null;
}

export interface TransformSpec {
  id: string;
  version: string;
  family: string;
  description: string;
  varieties: string[];
  params: TransformParam[];
  seeded: boolean;
  reversible: boolean;
}

export interface ChainStepIn {
  transform_id: string;
  params: Record<string, unknown>;
}

export type Piece = [number, number, string];

export interface StepOut {
  transform_id: string;
  version: string;
  family: string;
  params: Record<string, unknown>;
  seed: number;
  output: string;
  edits: number;
  valid: boolean;
  checks: Record<string, boolean | null>;
  notes: string[];
  provenance: Record<string, unknown>;
  pieces: Piece[];
}

export interface ApplyResult {
  original: string;
  original_sha256: string;
  output: string;
  output_sha256: string;
  variety: string;
  seed: number;
  chain_hash: string;
  valid: boolean;
  steps: StepOut[];
  pieces: Piece[];
}

export interface GenerateResult {
  recipe_hash: string;
  created: number;
  skipped_existing: number;
  invalid: number;
}

// ---- Annotation (v1) ----
export interface AnnotatorRow {
  pseudonym: string;
  proficiency: Record<string, string>;
  annotations: number;
}
export interface GuidelineRow {
  version: string;
  title: string;
  body: string;
}
export interface QueueItem {
  task_id: number;
  guideline_version: string;
  language: string;
  source_text: string;
  variant_text: string;
  remaining: number;
}
export interface DisagreementRow {
  task_id: number;
  language: string;
  source_text: string;
  variant_text: string;
  labels: { annotator: string; semantic_label: string; safety_label: string }[];
}
export interface AgreementStats {
  field: string;
  tasks_annotated: number;
  tasks_with_two_or_more: number;
  annotations: number;
  alpha_nominal: number | null;
  pairwise_kappa: { annotators: [string, string]; items: number; kappa: number | null }[];
  label_counts: Record<string, number>;
  unsure_treated_as_missing: boolean;
  adjudicated: number;
  note: string;
}

// ---- Models & experiments (v1) ----
export type CapabilityName = "TOKENIZE" | "CLASSIFY" | "EMBED" | "GENERATE" | "VISION_INPUT" | "OCR";

export interface ModelInfo {
  key: string;
  model_id: string;
  adapter: string;
  capabilities: CapabilityName[];
  license: string;
  revision: string | null;
  languages: string[];
  approx_ram_gb: number;
  approx_disk_gb: number;
  notes: string;
  test_double: boolean;
  availability: "available" | "not_downloaded" | "dependency_missing" | "resources_insufficient";
  availability_detail: string;
  loaded: boolean;
}

export interface ModelsInfo {
  device: string;
  device_reason: string;
  resources: { available_ram_gb: number | null; free_disk_gb: number; cache_dir: string };
  models: ModelInfo[];
}

export interface InferResult {
  model: string;
  capability: string;
  raw_output: unknown;
  normalized: Record<string, unknown>;
  latency_ms: number;
  tokenization: { tokens: string[]; ids: number[]; offsets: ([number, number] | null)[]; unknown: number } | null;
  metadata: { model_id: string; revision: string | null; device: string; adapter_version: string; test_double: boolean; library_versions: Record<string, string> };
  error: { code: string; message: string } | null;
}

export type ExperimentStatus = "queued" | "running" | "cancelling" | "cancelled" | "completed" | "failed" | "interrupted";

export interface ExperimentRow {
  id: number;
  name: string;
  status: ExperimentStatus;
  config: Record<string, unknown>;
  config_hash: string;
  total_items: number;
  done_items: number;
  failed_items: number;
  cancel_requested: boolean;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  uses_test_doubles: boolean;
}

export interface OutputRow {
  id: number;
  model_key: string;
  model_id: string;
  revision: string | null;
  test_double: boolean;
  source_id: string;
  variant_id: number | null;
  families: string | null;
  language: string;
  split: string | null;
  input_text: string;
  capability: string;
  modality: string;
  normalized: Record<string, unknown>;
  latency_ms: number;
  error: { code: string; message: string } | null;
  behavior: string | null;
  safety: string | null;
}

export interface RecipeRow {
  recipe_hash: string;
  families: string;
  seed: number;
  variants: number;
  invalid: number;
}

// ---- CRSC (v1, experimental) ----
export interface MetricRow {
  metric: "crsc_sem" | "crsc_safe";
  model: string;
  stratum: string;
  stratum_value: string;
  value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
  n_groups: number;
  details: Record<string, number | null>;
}
export interface CRSCResult {
  experiment_id: number;
  crsc_version: string;
  experimental: boolean;
  computed_at: string | null;
  resamples: number | null;
  seed: number | null;
  synthetic_fixture: boolean;
  test_double: boolean;
  research_reportable: boolean;
  results: MetricRow[];
}

// ---- Multimodal (v1) ----
export interface Reading {
  model: string;
  available: boolean;
  detail: string;
  text: string | null;
  confidence: number | null;
  latency_ms: number | null;
  error: { code: string; message: string } | null;
  comparison: {
    reference: string;
    reading: string;
    grapheme_error_rate: number | null;
    exact_match: boolean;
    nfkc_casefold_match: boolean;
    hidden_codepoints_in_original: number;
    hidden_codepoints_recovered: number;
  } | null;
  metadata: Record<string, unknown> | null;
}
export interface MultimodalResult {
  artifact_id: number;
  image_url: string;
  image_sha256: string;
  width: number;
  height: number;
  renderer: string;
  provenance: Record<string, unknown>;
  ocr: Reading | null;
  vlm: Reading | null;
}

// ---- EmojiGuard (v1) ----
export interface GuardContribution { source: string; name: string; weight: number; evidence_ids: string[]; detail: string }
export interface GuardAssessment {
  input_sha256: string;
  guard_version: string;
  ablation: string;
  evidence: { id: string; rule: string; category: string; cp_start: number; cp_end: number; utf16_start: number; utf16_end: number; message: string }[];
  indicators: Record<string, number>;
  rule_score: number | null;
  detector_score: number | null;
  detector_version: string | null;
  risk_score: number;
  uncertainty: string;
  contributions: GuardContribution[];
  explanation: string[];
  recommendation: string;
  relevant_views: string[];
  latency_ms: number;
  notes: string[];
}
export interface MetricsRow {
  n: number; tp: number; fp: number; tn: number; fn: number;
  precision: number | null; recall: number | null; f1: number | null; fpr: number | null; fnr: number | null;
  f1_ci: [number | null, number | null]; mean_latency_ms: number | null;
  false_positives: string[]; false_negatives: string[];
}
export interface GuardEvaluationResult {
  id: number;
  config: Record<string, unknown>;
  research_reportable: boolean;
  results: {
    systems: Record<string, { kind: "baseline" | "emojiguard"; overall: MetricsRow; strata: Record<string, Record<string, MetricsRow>> }>;
    unavailable: Record<string, string>;
    items: Record<string, { text: string; label: number; language: string; family: string }>;
  };
}
