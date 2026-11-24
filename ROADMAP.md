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
  - *Pending:* first green run on GitHub Actions
- [ ] Research foundation: proposal, objectives and threat model are drafted; the **literature review with verified references** is not done yet

## Week 2 — Unicode Forensics
- [ ] Evidence classifier (legitimate_structure / informational / anomalous / suspicious / concealed_payload_decoded)
- [ ] Recognition of legitimate structures: RGI emoji ZWJ sequences, VS15/VS16, modifiers, keycaps, subdivision flags, and Indic ZWJ/ZWNJ after a virama
- [ ] Mixed-script and homoglyph detection (confusables data)
- [ ] Recognized decoders: tag-character ASCII, variation-selector byte encoding (documented schemes only)
- [ ] Derived views (NFC, NFKC, sanitized, demojized, decoded) with offset maps back to the original
- [ ] Inspector: evidence panel, derived-view comparison, character-level highlighting

## Week 3 — Multilingual and Dataset Foundation
- [ ] Script detection and language metadata for en, hi, gu, hi-Latn and gu-Latn, recording uncertainty
- [ ] CLDR emoji annotations (en, hi, gu)
- [ ] M1 migration: datasets, sources, versions and manifests
- [ ] JSONL import with schema validation, hashing and duplicate detection
- [ ] Group-aware frozen splits and automated leakage tests
- [ ] Benign controls; synthetic fixtures tracked separately
- [ ] Dataset Explorer page

## Week 4 — Transformation Engine
- [ ] Six families (Unicode smuggling, emoji substitution, emoji cipher, homoglyph, text obfuscation, code-mixing) plus identity
- [ ] Versioned, seeded, provenance-tracked transformation chains with offset maps
- [ ] M2 migration: variants and provenance
- [ ] Transformation Laboratory page; reproducibility tests

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
