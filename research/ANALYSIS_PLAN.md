# Statistical analysis plan (DRAFT v0.1, not yet frozen)

Status: **draft.** This plan must be reviewed and frozen (its SHA-256 recorded in
`research/configs/LOCK.json`) **before** any eligible run is started. Results from runs started
earlier cannot be used to test these hypotheses. Every deviation after the freeze goes in the deviation
log at the end of this file, with its date and reason.

## Scope and units
- **Unit of analysis:** the source group. Every interval is a group-level bootstrap
  (`research/CRSC_SPECIFICATION.md`, "Uncertainty").
- **Data:** frozen evaluation dataset versions only. Pairs come from the test split. The train split is
  reserved for fitting the EmojiGuard detector.
- **Exclusions:** a run is analysed only if it passes every rule in `emojilens_core.repro.eligibility`
  (v1.0). Within a run, missing or errored outputs are excluded and counted, never imputed.
- **Minimum sample:** a stratum is reported only with at least 30 source groups. Smaller strata are
  shown as "insufficient data", not as estimates.

## Hypotheses

| ID | Statement | Metric | Comparison | Decision rule | Currently testable? |
|---|---|---|---|---|---|
| H1 | For at least one model, meaning-preserving variants change safety decisions more often than identity controls do. | CRSC-safe (with `unsafe_to_safe` and `safe_to_unsafe` reported) | meaning-preserving families vs identity, per model | the 95% bootstrap CI of the difference (identity − variant) lies above 0 | **No.** No catalogue model has task `safety` (`docs/MODEL_SUITABILITY.md`). A licensed safety classifier must be added first. |
| H2 | CRSC-sem agrees with human equivalence labels better than a lexical baseline does. | AUROC of the pair score for `equivalent` vs `not_equivalent` | CRSC-sem vs normalized character-bigram Jaccard | the CI of the AUROC difference lies above 0 | **No.** It needs adjudicated human labels (`research/ANNOTATION_PLAN.md`) and the embedding model on the M4. |
| H3 | EmojiGuard reaches higher recall than the strip-invisibles and NFKC baselines, at a false-positive rate on benign Indic and emoji controls that is no worse. | recall on constructive positives, FPR on benign controls | EmojiGuard vs each baseline | recall CI difference > 0, **and** FPR CI difference upper bound ≤ 0.02 | **Partly.** The pipeline runs, but it needs a real evaluation dataset with benign Indic and emoji controls. |
| H4 | Robustness differs by language variety: romanized varieties (hi-Latn, gu-Latn) show lower CRSC-sem under transformation than native scripts. | CRSC-sem per variety | hi-Latn vs hi, gu-Latn vs gu, per model | the CI of the difference lies below 0 | **No.** It needs the embedding model and enough groups per variety. |

H4 is new relative to `PROPOSAL.md`. It is added here, before any eligible run, and is exploratory unless
confirmed by the freeze.

## Multiplicity
Holm–Bonferroni across the confirmatory family {H1, H2, H3, H4} × models, at α = 0.05. Stratum-level
results (language, family, modality) are **exploratory** and labelled as such. They come without
p-values.

## Fixed settings
- Bootstrap: B = 10,000 for confirmatory tests and B = 2,000 for exploratory strata, with seed 20261126.
- Transformation seeds and recipe hashes come from the frozen config. No re-generation after a run starts.
- Models are pinned by revision. A run on a different revision is a new run.
- Stopping rule: one run per frozen config. Re-running after seeing results needs a new frozen config
  and an entry in the deviation log.

## What is never claimed
- Embedding similarity is not meaning equivalence (CRSC-sem is validated against human labels or it is
  not interpreted).
- Sentiment, refusal or response behaviour is never read as a safety judgment.
- Synthetic-fixture or test-double results are never findings.

## Deviation log
| Date | Change | Reason |
|---|---|---|
| — | — | — |
