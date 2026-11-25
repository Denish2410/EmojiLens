# Acceptance matrix

Status as of 2026-11-26, using these levels:
**Not started** · **Implemented** (code exists) · **Fixture-tested** (automated tests with fixtures or
labelled test doubles) · **Real-model verified** (executed with real models or engines) · **Research
validated** (used in an eligible run and checked against human labels) · **Blocked** (needs something
outside this workspace) · **Fully accepted** (every criterion verified).

Fixture testing never counts as real-model verification, and real-model verification never counts as
research validation.

| Area | Status | Evidence | What is missing |
|---|---|---|---|
| Unicode forensics (W2) | **Fully accepted** | unit, property and E2E tests; Inspector | — |
| Language-variety identification, CMI (W3) | Fixture-tested | unit tests, Multilingual Lab E2E | validation on a real labelled corpus |
| Datasets, group-aware splits, leakage checks (W3) | Fixture-tested | unit + API + E2E | a real licensed evaluation dataset (**Blocked**) |
| Transformation engine, six families + identity (W4) | **Fully accepted** (engineering) | determinism, provenance and validation tests | native-speaker lexicon review |
| Human annotation workflow, agreement (W5) | Fixture-tested | API + E2E | annotators (**Blocked**) |
| Adapter framework, registry, SafetyJudge (W6) | **Fully accepted** (framework) | test-double contract tests | — |
| Model task gate (no sentiment-as-safety) | **Fully accepted** (engineering) | API, worker and UI tests; `docs/MODEL_SUITABILITY.md` | — |
| HF classifier, embedding and generative adapters | Implemented | contract tests; `real_model` tests written | model downloads (**Blocked**: huggingface.co unreachable here) |
| Tesseract OCR adapter | **Real-model verified** (eng, hin) | `real_ocr` tests; validation run 5/5 | `guj` pack locally (installed in CI) |
| Experiment runner: cancel, interrupt, resume, run environments (W6, M8) | **Fully accepted** (engineering) | API tests, E2E | — |
| CRSC-sem / CRSC-safe (W7) | Fixture-tested (experimental) | math sanity, bootstrap tests | real outputs; validation against human labels |
| Sandboxed renderer + OCR path (W8) | **Real-model verified** | Chromium + Tesseract in tests and E2E | — |
| VLM path (adapter + `vlm` modality) | Fixture-tested | test-double runs with real Chromium render | VLM weights (**Blocked**) |
| EmojiGuard rules, detector, 5 baselines, 5 ablations (W9) | Fixture-tested | unit + API + E2E on the synthetic fixture | real evaluation data |
| Dashboard summary and Overview | **Fully accepted** (engineering) | API + unit + E2E | — |
| Settings and system page | **Fully accepted** (engineering) | API + unit + E2E; no-private-data test | — |
| 13 frontend pages, responsive | **Fully accepted** (engineering) | no-overflow E2E on 13 routes × desktop/mobile; audit at 1440/820/390/360 px | — |
| Preflight and M4 smoke validation (G) | Real-model verified (Tesseract only) | unit tests; real run recorded in TEST_REPORT | an M4 run with all models |
| Eligibility rules and manifests (I) | **Fully accepted** (engineering) | core + API tests | — |
| Config freezing and lock (I) | **Fully accepted** (engineering) | unit + script tests; CI check | analysis plan not yet frozen |
| Report from eligible runs only (I) | **Fully accepted** (engineering) | API tests (ineligible runs excluded) | an eligible run to report |
| Fresh-clone verification (I) | **Fully accepted** | `scripts/verify_fresh_clone.sh` passed on d9d4d2a | — |
| Analysis plan (H) | Implemented (draft) | `research/ANALYSIS_PLAN.md` | review and freeze |
| Literature review | Blocked | — | verified references |
| Research results | **Not started** | the report generator states "no eligible runs" | everything above marked Blocked |

## Release tag
**Not created.** A release requires real-model verification of the HF adapters, an eligible run, and
a frozen analysis plan. None of these can be completed in this workspace.
