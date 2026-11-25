# Research readiness

The Overview dashboard (`GET /api/v1/dashboard/summary`) checks the first five items live. A run's own
readiness is `GET /api/v1/experiments/<id>/eligibility`.

| # | Requirement | How it is checked | Status (2026-11-26) |
|---|---|---|---|
| 1 | Frozen evaluation dataset (licensed, multilingual, benign Indic and emoji controls) | dashboard `evaluation_dataset` | ❌ Only the synthetic fixture exists |
| 2 | Human annotations with measured agreement | dashboard `human_annotation`, Annotation Studio agreement | ❌ No annotators recruited |
| 3 | Real neural model installed and pinned | dashboard `real_model`, `scripts/validate_models.py` | ❌ huggingface.co is blocked in the cloud workspace; pending on the M4 |
| 4 | OCR with eng, hin and guj packs | dashboard `ocr`, `scripts/preflight.py` | ⚠️ Tesseract eng+hin locally; guj only in CI |
| 5 | Eligible run | dashboard `reportable_experiment` | ❌ |
| 6 | Analysis plan frozen | `research/configs/LOCK.json` contains `research/ANALYSIS_PLAN.md` | ❌ Draft |
| 7 | Safety classifier (task `safety`) for H1 | `docs/MODEL_SUITABILITY.md` | ❌ None in the catalogue |
| 8 | Verified literature review | `research/LITERATURE_REVIEW.md` has verified entries | ❌ |

## Order of work on the M4
1. `scripts/preflight.py --network`, then `scripts/setup_models.py`, then `scripts/validate_models.py` (items 3 and 4).
2. Source and license an evaluation dataset; import and freeze it (item 1).
3. Recruit annotators; run the annotation workflow (item 2).
4. Review and freeze the analysis plan and configs (`scripts/freeze_configs.py`) (item 6).
5. Run the frozen configs; check eligibility; generate the report (item 5).
