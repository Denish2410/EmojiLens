# Project Status

**Last updated:** 2026-11-25
**Current phase:** Weeks 6–9 engineering is implemented. Real-model inference, human annotation and
final experiments (Week 10) are blocked on external dependencies.

Status legend: **Implemented** (code exists) · **Fixture-tested** (automated tests with fixtures or
labelled test doubles) · **Real-verified** (executed with real models or engines) · **Awaiting
external** (needs something outside this workspace) · **Accepted** (all acceptance criteria verified).
Fixture-only testing never counts as real-model validation.

| Area | Implemented | Fixture-tested | Real-verified | Awaiting external | Accepted |
|---|---|---|---|---|---|
| W1 foundation, CI | ✅ | ✅ | n/a | literature review (verified refs) | ⬜ |
| W2 Unicode forensics | ✅ | ✅ | n/a | — | ✅ |
| W3 multilingual and datasets | ✅ | ✅ | n/a | semantic comparison needs embeddings | ⬜ |
| W4 transformations | ✅ | ✅ | n/a | native-speaker lexicon review | ✅ (engineering) |
| W5 annotation infrastructure | ✅ | ✅ | n/a | **annotators** (no human labels exist) | ⬜ |
| W6 adapter framework, registry, device, SafetyJudge | ✅ | ✅ (test doubles) | — | — | ✅ (framework) |
| W6 HF classifier / embedding / generative / VLM adapters | ✅ | contract only | ❌ never run | **model downloads** (huggingface.co blocked) | ⬜ |
| W6 Tesseract OCR adapter | ✅ | ✅ | ✅ eng + hin (guj pack missing locally) | guj traineddata (installed in CI) | ⬜ (guj) |
| W6 M4, experiment jobs, cancel/interrupt/resume | ✅ | ✅ | ✅ with Tesseract in the `ocr` modality | — | ✅ |
| W6 Model Arena, Experiment Studio | ✅ | ✅ unit + E2E | — | real models to compare | ⬜ |
| W7 CRSC-sem / CRSC-safe (experimental), M5 | ✅ | ✅ math sanity | ❌ | real model outputs | ⬜ |
| W7 CRSC Analytics | ✅ | ✅ | — | — | ⬜ |
| W8 sandboxed renderer, OCR path, M6 | ✅ | ✅ | ✅ Chromium + Tesseract (en, hi) | — | ⬜ (VLM) |
| W8 VLM path (adapter + `vlm` experiment modality) | ✅ | ✅ (test double, real Chromium render) | ❌ never run | **model downloads** | ⬜ |
| Model task / safety-eligibility gate, language coverage | ✅ | ✅ | n/a | — | ✅ (engineering) |
| W8 Multimodal Laboratory | ✅ | ✅ unit + E2E | ✅ real render/OCR in E2E | — | ⬜ |
| W9 EmojiGuard rules, view re-scoring, policy | ✅ | ✅ | n/a | — | ⬜ (needs real evaluation) |
| W9 learned detector, baselines, ablations, M7 | ✅ | ✅ (synthetic fixture only) | n/a | real evaluation data | ⬜ |
| W9 off-the-shelf classifier baseline | reported as unavailable | — | ❌ | **model downloads** | ⬜ |
| W9 EmojiGuard Console, Evaluation Dashboard | ✅ | ✅ unit + E2E | — | — | ⬜ |
| W10 final experiments, report, release | ⬜ | ⬜ | ⬜ | all of the above | ⬜ |

## Research results
**None.** All numbers that have appeared anywhere came from synthetic fixtures or labelled test
doubles and are flagged "not research-reportable" in the UI and API. No human annotations exist.

## External blockers
1. **Model weights:** huggingface.co is unreachable from the cloud workspace. Run `docs/MODEL_SETUP_M4.md`
   on the M4 Mac, or allow huggingface.co in claude.ai Settings → Capabilities.
2. **Human annotators:** see `research/ANNOTATION_PLAN.md`.
3. **Gujarati OCR pack** (`guj`) is missing locally. CI installs it.
4. **Literature review:** the references still need verification (no verified entries yet).
5. **Evaluation dataset:** a real, licensed multilingual evaluation dataset has not been sourced. The only
   data in the repository is the 28-record synthetic fixture.

## Remaining engineering work
- `real_model` integration tests that execute each HF adapter (to run on the M4).
- An Overview dashboard refresh (model availability, experiment status, dataset statistics).
- A Settings and System page (spec M).
- Week 10: frozen research configurations, a report generated from stored results, a fresh-clone check and a release tag.

## Latest verified checkpoint
See `git log -1 origin/main`. GitHub Actions was green through run #11; later runs are checked at each push.

## Next exact task
On the M4 Mac: run `scripts/setup_models.py` for the embedding, generative and classifier models, then
run `uv run pytest -m "real_model or real_ocr"` and record the results in `docs/TEST_REPORT.md`. In parallel,
add `real_model` integration tests that execute each HF adapter, so real-inference acceptance can be ticked.
