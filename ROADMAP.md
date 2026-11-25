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
- [x] M3 migration: annotators (pseudonym + proficiency), immutable guideline versions, tasks, annotations, adjudications
- [x] Seeded, language-stratified task sampling; blinded per-annotator queues; independent submissions
- [x] Cohen's kappa (pairwise) and nominal Krippendorff's alpha, with "unsure" treated as missing and undefined values reported as undefined
  - *AC:* hand-computed values reproduced in tests
- [x] Disagreement inspection and adjudication that keeps raw labels
- [x] Annotation Studio page (unit + E2E); draft guidelines (`research/ANNOTATION_GUIDELINES.md`)
- [ ] **Real human annotation of ~100–150 pairs, at least two annotators on a stratified subset: blocked on recruitment (external dependency)**

## Week 6 — Models and Experiment Runner
- [x] Adapter interface (TOKENIZE, CLASSIFY, EMBED, GENERATE, VISION_INPUT, OCR), metadata, tokenization traces, structured errors, lazy loading, LRU-bounded registry, CPU/MPS/CUDA selection, resource checks, availability detection
- [x] SafetyJudge (response behaviour kept separate from safe/unsafe/unknown; a refusal is never treated as unsafe)
- [x] M4: model versions, persistent experiments (cancel, interrupted-on-restart, resume), model outputs
- [x] Model Arena, Experiment Studio (unit + E2E, three widths)
- [x] Pinned-revision setup script and `docs/MODEL_SETUP_M4.md`
- [x] Tesseract OCR adapter: **real inference verified** (eng, hin)
- [ ] **Real inference with HF classifier, embedding, generative and VLM models: blocked (no access to huggingface.co)**

## Week 7 — Consistency and Evaluation
- [x] CRSC specification v0.1 (`research/CRSC_SPECIFICATION.md`), separate CRSC-sem and CRSC-safe, group bootstrap CIs, flips, unknown and missing, stratification, identity controls (math sanity tests)
- [x] M5 metric storage; compute and read API; not-reportable flags
- [x] CRSC Analytics page
- [ ] CRSC on real model outputs; comparison with human equivalence (blocked: models and annotators)

## Week 8 — Multimodal
- [x] Sandboxed Chromium renderer (escaped text, JS off, CSP, all requests aborted) with hash and provenance; Pillow fallback flagged
- [x] Real render → Tesseract OCR path with grapheme-error comparison; `ocr` experiment modality
- [x] M6 render artifacts; served by id with path containment
- [x] Multimodal Laboratory
- [ ] VLM path with a real model (blocked); Gujarati OCR locally (pack missing; installed in CI)

## Week 9 — EmojiGuard
- [x] Rule engine with documented weights, located evidence, derived-view re-scoring, policy recommendations (block opt-in)
- [x] Interpretable logistic detector (train split only, hash-verified artifacts, uncalibrated)
- [x] Baselines (no defence, strip-invisibles, NFKC, keyword) and ablations (rules only, detector only, without decoders, without view re-scoring, without Indic awareness)
- [x] Metrics with F1 bootstrap CIs, FP/FN inspection; M7
- [x] EmojiGuard Console, Evaluation Dashboard
- [ ] Off-the-shelf safety-classifier baseline (needs a model); evaluation on real data

## Week 10 — Final Experiments and Release
- [x] Config-freezing tooling with a CI-verified lock; reproducibility manifests; eligibility rules
- [x] Report generator that uses eligible stored outputs only
- [x] Settings and System page; Overview dashboard; full regression; fresh-clone verification
- [ ] Freeze the analysis plan and configs; run real experiments; generate the final report (**blocked**: models, data, annotators)
- [ ] Screen-reader accessibility review; release tag (only after the item above)
