# Changelog

All notable changes are documented here. Format based on Keep a Changelog.

## [Unreleased]
### Added
- Week 2 Unicode forensics: contextual evidence classifier (5 categories, ruleset 0.2.0), legitimate
  emoji/Indic/Arabic structure recognition, mixed-script and whole-script homoglyph detection,
  tag-ASCII and variation-selector byte decoders, reversible derived views, Inspector evidence and
  view panels.
- `scripts/source_hygiene.py` and a repository test that rejects raw invisible or confusable characters
  in source code.
- Week 3: language-variety identification with uncertainty and CMI, CLDR 49 emoji meanings,
  M1 dataset storage, strict JSONL import, group-aware frozen splits, leakage validation, a synthetic
  benign-control fixture, Dataset Explorer and Multilingual Lab pages.
- Week 4: transformation engine (identity and six families, seeded and versioned, with provenance,
  piece maps, validation and composable chains), M2 variants, transform and variant-generation
  endpoints, Transformation Laboratory, transformation taxonomy.
- Week 5: human annotation workflow (M3, blinded queues, independent submissions, adjudication),
  Cohen's kappa and Krippendorff's alpha, Annotation Studio, draft guidelines.
- Weeks 6–9: model adapter framework, SafetyJudge, real Tesseract OCR, pinned-revision setup, M4 experiments
  with cancel, interrupt and resume; CRSC-sem and CRSC-safe (experimental) with group bootstrap, M5; sandboxed
  Chromium renderer and OCR path, M6; EmojiGuard rules, detector, baselines and ablations, M7; Model Arena,
  Experiment Studio, CRSC Analytics, Multimodal Laboratory, EmojiGuard Console, Evaluation Dashboard.
- Model `task` metadata, `docs/MODEL_SUITABILITY.md`, and per-output language coverage
  (`_language`, `_language_supported`).
- `vlm` experiment modality (render, then VISION_INPUT) with an optional prompt; Experiment Studio
  modality selection.
- Dashboard summary endpoint and an Overview rebuilt from stored data; Settings and system page
  (`/system/info`) with no paths or hostnames exposed.
- `emojilens_core.repro`: shareable environment metadata, `scripts/preflight.py`, M4 smoke validation
  (`scripts/validate_models.py`) with OCR/VLM GER read-back, and `docs/M4_VALIDATION.md`.
- M8 `run_environments`; research-eligibility rules v1.0; `/experiments/{id}/eligibility` and `/manifest`;
  eligibility panel and manifest download in Experiment Studio.
- Report generator from eligible runs only (`/reports/research(.md)`, `scripts/generate_report.py`).
- Config freezing with a lock checked in CI (`scripts/freeze_configs.py`); draft analysis plan, experiment
  card, results template and readiness checklist; `real_model` integration tests;
  `scripts/verify_fresh_clone.sh`.
- E2E: Overview, Settings and a no-overflow check on every page.
### Fixed
- `/models` no longer exposes the absolute model cache path.
- Pages overflowed the viewport on phones (Transformation Lab, Annotation Studio) and on tablets
  (Evaluation actions).
- Non-safety classifiers (the sentiment model) can no longer have their labels mapped to safety
  judgments (API, worker and UI).
- Annotation submit race (form now disabled while a submission is pending) and the flaky annotation E2E (CI #8).
- API registry now applies model pins (wiring missing in bfb7d0c).
- `.gitignore` `models/` also ignored the source package; anchored to `/models/`.
- Raw invisible characters in test fixtures and the Inspector sample are now written as escapes.
- Vitest no longer collects Playwright specs.
- Monorepo foundation (uv and pnpm workspaces), project rules and memory files.
- `emojilens_core.unicode`: input validation (`invalid_unicode`), SHA-256 of the original UTF-8,
  grapheme segmentation, code point inspection, and code point / UTF-8 / UTF-16 offset mapping.
- API v1: `/health`, `/ready`, `POST /unicode/analyze`; structured errors; input size limit.
- Database foundation M0 (SQLite WAL, Alembic).
- Web console shell with Overview and Unicode Inspector; dark and light themes; mobile drawer.
- CI workflow; Vitest, Pytest/Hypothesis and Playwright test suites.
