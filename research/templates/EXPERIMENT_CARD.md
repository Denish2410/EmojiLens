# Experiment card: <name>

Fill this in **before** starting the run, and freeze it together with the config.

| Field | Value |
|---|---|
| Hypothesis | H? (`research/ANALYSIS_PLAN.md`) or "exploratory" |
| Frozen config | `research/configs/<file>.json`, SHA-256 `<from LOCK.json>` |
| Dataset | slug, version, content SHA-256, split seed (frozen?) |
| Recipes | recipe hashes and the families they apply |
| Models | key @ revision, device, task (only `safety` models may produce safety judgments) |
| Modalities | text / ocr / vlm (VLM prompt, if any) |
| Expected eligibility | every rule in `emojilens_core.repro.eligibility` v1.0 met? |
| Known limitations | language coverage gaps, missing OCR packs, annotation status |

## After the run
- Experiment id, `GET /api/v1/experiments/<id>/eligibility` result (paste the blocking reasons if any).
- Manifest: `GET /api/v1/experiments/<id>/manifest`. Record the outputs digest.
- Report: `scripts/generate_report.py`. Link the report directory.
- Deviations from this card (each also goes in the analysis-plan deviation log).
