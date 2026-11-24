# EmojiLens Roadmap

The mandatory scope is defined in the master specification. Work proceeds in dependency order.
A box is ticked only after its acceptance criteria have been verified (see `docs/TEST_REPORT.md`).
The timeline is roughly 10 weeks at 2–3 hours per day, and it is extended rather than cut.

## Week 1 — Foundation
- [x] Monorepo layout: uv workspace (`packages/core`, `apps/api`) and pnpm workspace (`apps/web`)
- [x] Project memory files (CLAUDE.md, PROJECT_STATUS.md, ROADMAP.md, CHANGELOG.md, docs/DECISIONS.md, docs/TEST_REPORT.md)
- [x] Original-input SHA-256 over strict UTF-8; lone surrogates rejected with `invalid_unicode`
  - *AC:* property test confirms the digest equals sha256(utf-8) for arbitrary scalar text; surrogate tests pass
- [x] Extended grapheme segmentation (UAX #29)
  - *AC:* property test confirms the graphemes concatenate back to the input; ZWJ family, skin tone, keycap, flag and subdivision flag each form one grapheme
- [x] Code point, UTF-8 and UTF-16 offset mapping
  - *AC:* property tests check spans against Python's encoders and the UTF-16 round trip
- [x] M0 database foundation: SQLite WAL, foreign keys on, Alembic upgrade and downgrade tested
- [x] `POST /api/v1/unicode/analyze`, `/health` and `/ready` with structured errors and an input size limit
- [x] Web shell: sidebar, mobile drawer, breadcrumbs, theme switch, toasts, skip link
- [x] Unicode Inspector shell: editor, grapheme strip, code point table, UTF-8/UTF-16 offsets, invisible markers, copy original
- [x] CI workflow: ruff, mypy, pytest, tsc, eslint, vitest, build, Playwright
  - Verified: GitHub Actions run #2 green (backend, frontend, E2E)
- [ ] Research foundation: proposal, objectives and threat model are drafted; the **literature review with verified references** is not done yet

## Week 2 — Unicode Forensics
- [x] Evidence classifier (legitimate_structure / informational / anomalous / suspicious / concealed_payload_decoded)
  - *AC:* benign English, Hindi, Gujarati, Hinglish, Gujlish and heavy-emoji controls never exceed informational (tested)
- [x] Recognition of legitimate structures: RGI emoji ZWJ sequences, VS16 presentation, modifiers, keycaps, flags, subdivision flags; ZWJ/ZWNJ after an Indic virama; Arabic-script ZWNJ
- [x] Mixed-script words with Latin look-alikes and whole-script confusables (confusables snapshot, see D-009)
- [x] Recognized decoders: tag-character ASCII, variation-selector byte encoding; undecodable runs flagged, never guessed
- [x] Derived views (original, NFC, NFKC, sanitized, demojized, decoded) as segment lists that tile the original
  - *AC:* property tests confirm tiling and equality with whole-string NFC/NFKC
- [x] Inspector: evidence panel, derived-view tabs, cross-panel character highlighting (unit + E2E tests)
- [x] Source hygiene guard: no raw invisible/confusable characters in source files

## Week 3 — Multilingual and Dataset Foundation
- [x] Variety identification for en, hi, gu, hi-Latn and gu-Latn that records uncertainty (thin evidence, margin, unknown tokens); CMI and switch points
  - *AC:* each variety identified on test sentences; unknown text is left undetermined rather than guessed (tested)
- [x] CLDR 49 emoji annotations (en, hi, gu, hi-Latn), vendored with the license; gu-Latn fallbacks flagged
- [x] M1 migration: datasets, versions, sources; a test asserts ORM and migrations agree
- [x] JSONL import: strict schema v1, line-numbered errors that don't echo text, all-or-nothing, content hash, exact and normalized duplicate detection, upload size limit
- [x] Group-aware frozen splits (deterministic per-group hashing) and automated leakage tests (core, API, E2E)
- [x] Benign controls: 28-record synthetic fixture across five varieties, never escalated above informational (tested); synthetic datasets flagged and excluded from results
- [x] Dataset Explorer and Multilingual Laboratory pages (unit + E2E)
- [x] Annotation recruitment preparation (`research/ANNOTATION_PLAN.md`); **recruitment itself is an external dependency**
- [ ] Multilingual *semantic* comparison (needs the embedding adapter, Week 6)

## Week 4 — Transformation Engine
- [x] Six families (Unicode smuggling, emoji substitution, emoji cipher, homoglyph, text obfuscation, code-mixing) plus identity, each with id, version, description, varieties, validated parameters, seed, provenance, offset map and validation
- [x] Reproducible chains with composed offset maps and a canonical chain hash (property-tested)
- [x] M2 migration: variants with recipe and chain hashes, piece maps, per-step results and inherited splits
- [x] Variant generation only for frozen versions; leakage checks cover variants
- [x] Transformation Laboratory (chain builder, provenance, reproducibility, offset map, variant generation)
- [x] Taxonomy documented (`research/TRANSFORMATION_TAXONOMY.md`)
  - *AC:* identity leaves input unchanged; every smuggling technique is detected by the Week 2 evidence rules (tested)

## Week 5 — Human Annotation
- [ ] M3 migration: annotators and annotations; versioned guidelines
- [ ] Blinded queues, adjudication, Cohen's kappa and Krippendorff's alpha
- [ ] Annotation Studio page
- [ ] Real annotation of about 100–150 pairs, with at least two annotators on a stratified subset (**external dependency: annotators**)

## Week 6 — Models and Experiment Runner
- [ ] Adapter interface (TOKENIZE, CLASSIFY, EMBED, GENERATE, VISION_INPUT, OCR)
- [ ] Hugging Face classifier, Sentence Transformers embedding and small local generative model adapters (needs model selection and a resource check)
- [ ] SafetyJudge that keeps response behaviour separate from the safety judgment
- [ ] M4 migration: model versions, experiments and outputs; non-blocking worker with cancellation
- [ ] Model Arena and Experiment Studio pages

## Week 7 — Consistency and Evaluation
- [ ] CRSC-sem and CRSC-safe specification (math), then implementation
- [ ] Group-level bootstrap 95% CIs; flip counts; stratification
- [ ] M5 migration; baselines; CRSC Analytics page

## Week 8 — Multimodal
- [ ] Sandboxed Chromium renderer (no external resources), image hashing and provenance
- [ ] Tesseract OCR for eng, hin and guj (**guj pack missing in the current dev container**)
- [ ] Local VLM adapter; M6 migration; Multimodal Laboratory page

## Week 9 — EmojiGuard
- [ ] Rule engine, learned detector (scikit-learn, group-aware), explainable aggregation and recommendations
- [ ] M7 migration; baselines and ablations; FP/FN inspection; EmojiGuard Console and Evaluation Dashboard

## Week 10 — Final Experiments and Release
- [ ] Freeze configs, run real experiments, final report generated from stored results
- [ ] Settings and System page; full regression; fresh-clone verification; accessibility review; release tag
