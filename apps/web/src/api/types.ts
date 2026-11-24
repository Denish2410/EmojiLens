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
  engine: { engine_version: string; unicodedata_version: string; regex_version: string };
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
