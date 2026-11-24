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
