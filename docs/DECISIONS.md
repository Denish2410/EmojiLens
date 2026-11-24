# Architecture Decision Log

## D-001 Monorepo with uv and pnpm workspaces (2026-11-24)
**Decision:** a single repository. The Python members are `packages/core` (engine) and `apps/api`.
The JS member is `apps/web`.
**Alternatives:** separate repositories; a single Python package that serves a static frontend.
**Rationale:** the engine stays independently testable, the API contracts sit next to their
consumers, and CI is atomic.
**Tradeoff:** two toolchains. CI runs them as separate jobs.

## D-002 Grapheme segmentation via `regex` `\X` (2026-11-24)
**Decision:** use the `regex` package's extended grapheme cluster support.
**Rationale:** it is maintained, implements UAX #29 including emoji ZWJ sequences, and is
already in the approved stack.
**Tradeoff:** the Unicode version of `regex` can differ from Python's `unicodedata`
(14.0 on Python 3.11). Both versions are reported in every analysis response so results stay
reproducible. *Unresolved:* whether to pin a single Unicode version across the engine
(re-evaluate in Week 2 together with the emoji data source).

## D-003 Markers are descriptive, not verdicts (2026-11-24)
**Decision:** the Week 1 code point `kinds` (zero_width, joiner, tag, bidi_control, and so on)
describe structure only. Risk evidence categories come from a separate contextual classifier
in Week 2.
**Rationale:** ZWJ and ZWNJ are legitimate in emoji sequences and in Devanagari and Gujarati
text. Flagging them by type alone would cause systematic false positives on Indic content.

## D-004 Offsets in three index spaces (2026-11-24)
**Decision:** every span carries code point, UTF-8 byte and UTF-16 code unit offsets.
**Rationale:** Python indexes by code points, the browser by UTF-16 units, and hashing and
storage work on UTF-8 bytes. Evidence must be locatable in every layer.

## D-005 Readiness requires the migration head (2026-11-24)
**Decision:** `/api/v1/ready` returns 503 unless the database is reachable and at the
Alembic head. The API never auto-migrates on startup. `scripts/dev-api.sh` migrates explicitly.

## D-006 TypeScript 5.9 rather than 7.x (2026-11-24)
**Decision:** pin `typescript@~5.9`.
**Rationale:** `typescript-eslint` 8.x refuses to run with TypeScript 7.
Revisit once typescript-eslint supports it.

## D-007 Navigation shows only implemented pages (2026-11-24)
**Decision:** a page is added to the sidebar only when it is functional and backed by real data.
**Rationale:** the specification forbids placeholder pages and non-functional UI elements.

## D-008 Evidence rules are contextual, with legitimate structure first (2026-11-24)
**Decision:** before any other rule runs, RGI emoji sequences (taken from the `emoji` package data)
and joiners after a virama (canonical combining class 9) are marked `legitimate_structure`.
Code points covered by legitimate structure are never escalated.
**Alternatives:** flagging by code point type alone. Rejected because it would systematically flag Indic
text and emoji-heavy messages.
**Tradeoff:** non-RGI vendor ZWJ sequences are reported as `informational`, not legitimate.

## D-009 Confusables data from `confusable_homoglyphs` (2026-11-24)
**Decision:** Latin look-alikes come from the MIT-licensed `confusable_homoglyphs` 3.3.1 package,
which bundles a snapshot of Unicode's confusables data.
**Reason:** unicode.org is not reachable from the current development environment.
**Limitation:** the snapshot predates the Unicode version used by `regex`, so newer look-alikes may be
missed. *Unresolved:* vendoring a current `confusables.txt` once it can be downloaded and verified.

## D-010 Only documented encodings are decoded (2026-11-24)
**Decision:** decode only (a) tag characters as an ASCII mirror and (b) variation selectors as one byte
each, accepted only when the bytes form valid UTF-8. Undecodable runs become `suspicious` with the raw
bytes as hex. Nothing is guessed, and decoded text is never executed or rendered as markup.

## D-011 Derived views as tiling segment lists (2026-11-24)
**Decision:** each view is a list of `(original span, view span, text)` segments that tile the original
exactly once. NFC and NFKC are applied per grapheme, falling back to a single segment if the
concatenation differs from whole-string normalization, so correctness never depends on segmentation.

## D-012 Heuristic, transparent language identification (2026-11-24)
**Decision:** use script plus seed-lexicon identification, with fractional counts for ambiguous words
and explicit uncertainty reasons, instead of a pretrained language-ID model.
**Rationale:** no model download is possible in this environment, and off-the-shelf language-ID models
rarely support hi-Latn or gu-Latn. A transparent baseline is auditable and cannot quietly fabricate certainty.
**Revisit:** when models can be downloaded, compare against a learned identifier on human-labelled data.

## D-013 CLDR annotations from the official cldr-json npm packages (2026-11-24)
**Decision:** vendor a derived subset (name and keywords for en, hi, gu, hi-Latn) of
`cldr-annotations-full` and `cldr-annotations-derived-full` 49.0.0, which are published by the Unicode CLDR
project under Unicode-3.0. `scripts/vendor_cldr_annotations.py` regenerates the subset reproducibly.
**Tradeoff:** 3.5 MB of vendored JSON in the package.

## D-014 Datasets are immutable versions; splits assigned at freeze (2026-11-24)
**Decision:** every import creates a new numbered version with a content hash. Freezing assigns splits
once, by hashing `seed:source_group`, and cannot be repeated (409). The leakage check runs at freeze time.
**Rationale:** group-level assignment happens before any transformation (Week 4), so all variants of a
source inherit its split, and adding groups never moves existing ones.

## D-015 Dataset upload as a raw request body (2026-11-24)
**Decision:** `POST /datasets/{slug}/versions` takes the JSONL as an `application/x-ndjson` body,
streamed with a byte limit, instead of multipart.
**Rationale:** no file is ever written to a path derived from user input (no path traversal), and no extra
dependency is needed.

## D-016 Piece maps as the single provenance format (2026-11-24)
**Decision:** transformations return `(orig_start, orig_end, text)` pieces that tile their input,
the same structure used by derived views (D-011). Chains compose piece maps by grouping at shared
mid-text boundaries.
**Rationale:** one offset-mapping primitive, so every multi-step output maps back to original offsets,
and property tests can check tiling generically.

## D-017 Recipe hash versus chain hash (2026-11-24)
**Decision:** a variant stores a *recipe hash* (seed, step ids, versions, resolved params) and a *chain hash*
(which also includes the source's variety). Idempotent generation and filtering use the recipe hash.
**Rationale:** one recipe applied to a multilingual dataset gives per-variety chains that still
belong to the same experimental condition.

## D-018 Harmless surrogate payloads only (2026-11-24)
**Decision:** payload parameters are free strings (at most 200 code points, well-formed). Defaults and
all fixtures use `SURROGATE-TOKEN`. The engine never ships harmful payloads, and nothing decoded is executed.

## D-019 Blinded queues and treatment of "unsure" (2026-11-24)
**Decision:** the queue returns only the source, the variant, the language and the guideline version, in
a per-annotator hash order. Agreement statistics treat `unsure` as missing, and undefined statistics are
`null`, never 0 or 1.
**Rationale:** this avoids anchoring on transformation families or on other annotators' labels, and avoids
reporting agreement that does not exist.

## D-020 Gates verify exactly the committed content (2026-11-24)
**Decision:** the local commit helper stashes all unstaged and untracked changes before running the
quality gates, so each commit is checked as committed.
**Context:** CI run #5 failed on a formatting difference that existed only in the committed file. The
working tree had been formatted, but that change was never staged.
