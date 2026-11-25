# Model suitability and safety-judgment eligibility

Every catalogue model declares a `task` (`packages/core/src/emojilens_core/models/types.py`,
`MODEL_TASKS`). Its task decides which conclusions its outputs can support. This page records those
limits so that no result is ever over-read. See D-026 in `docs/DECISIONS.md`.

## Rule

Only a model whose task is `safety` may feed a safety judgment (`safe` / `unsafe` / `uncertain`).
This is enforced in three places:

| Layer | Enforcement |
|---|---|
| API (`POST /experiments`) | a `label_map` alongside a CLASSIFY run on a non-safety model is rejected with `422 not_a_safety_classifier` |
| Worker | SafetyJudge runs only when `task == "safety"`, so an output stored without that check can never carry a `safety` value |
| UI (Experiment Studio) | the label-map field is disabled unless a selected model has task `safety` and runs on text or OCR input |

No model in the current catalogue has task `safety`. A test asserts this
(`test_every_catalogue_model_declares_its_task`). Today, safety judgments come only from the labelled
test double in automated tests, and those are never reportable (D-021).

## Catalogue

| Key | Task | Valid uses | Not valid for | Declared languages |
|---|---|---|---|---|
| `classifier-xlmr-sentiment` | sentiment | tokenization traces; prediction stability under transformation (label flips, score drift) as a robustness signal | safety, harm or toxicity judgments: a sentiment flip is not a safety change | en, hi |
| `embed-multilingual-minilm` | embedding | semantic consistency (CRSC-sem) between source and variant | safety judgments; equivalence claims without human validation | en, hi, gu |
| `gen-qwen2.5-0.5b-instruct` | generation | response-behaviour categories (answer / refusal / partial / error) | safety judgments: refusal alone is not proof that an input is unsafe | en, hi |
| `tesseract-ocr` | ocr | reading rendered text back for the OCR modality | anything beyond text recovery | en, hi, gu (guj pack required) |
| `vlm-smolvlm-256m` | vision_language | the `vlm` modality: image transcription and description | safety judgments; reading Indic scripts (not expected) | en |

## Language coverage

Every stored output records `_language` (from the source record) and `_language_supported`:

- `true`: the model's declared languages include the record's language.
- `false`: they don't. The output is still produced, because coverage is a property to study, not a
  reason to hide results. Analyses must stratify by it, and reports must not average across it unless
  they say so.
- `null`: the model declares no languages (test doubles), so coverage is unknown.

Romanized varieties (`hi-Latn`, `gu-Latn`) count as distinct from their native-script parents. A model
that declares `hi` is not assumed to cover `hi-Latn`.

## Adding a safety classifier

To add a real safety classifier, a model must have:

1. `task="safety"` and CLASSIFY in its catalogue entry.
2. A license verified on the model card, and a pinned revision (`scripts/setup_models.py`).
3. A documented label set, with the label map recorded in the experiment config (it is hashed).
4. Language coverage stated from the model card, not assumed.
5. A `real_model` test that executes it.

Until all five hold, its outputs are not used for safety conclusions.
