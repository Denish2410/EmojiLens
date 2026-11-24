# Project Status

**Current week:** 6 (AI models and experiment runner)
**Current milestone:** Weeks 2–5 are complete as infrastructure. Real human annotation awaits annotators. Outstanding: the Week 1 literature review and multilingual semantic comparison (needs Week 6 embeddings).
**Last updated:** 2026-11-24

## Completed (verified, see docs/TEST_REPORT.md)
- Monorepo and toolchain (uv workspace, pnpm workspace, lockfiles)
- Unicode engine core: validation, original-input hash, graphemes, code point inspection, 3-space offsets
- API v1: health, readiness, Unicode analysis, structured errors, size limit, OpenAPI
- DB foundation M0 (SQLite WAL, Alembic, migration tests)
- Web shell, Overview (live status), Unicode Inspector shell
- Playwright E2E against the real API
- GitHub Actions CI is green (run #2). Run #1 caught Vitest collecting the Playwright spec, now fixed.
- Research drafts: proposal, threat model; literature review skeleton

- Week 2: evidence classifier, legitimate-structure recognition, homoglyph detection, decoders, derived views, Inspector evidence and views UI, source hygiene guard
- Week 3: variety identification with uncertainty, CLDR 49 emoji meanings, M1 datasets, JSONL import, frozen group-aware splits, leakage validation, benign-control fixture, Dataset Explorer, Multilingual Lab
- Week 4: identity plus six transformation families, composable chains with offset maps, M2 variants, variant generation on frozen versions, Transformation Lab, taxonomy
- Week 5: M3 annotation storage, blinded queues, agreement statistics, adjudication, Annotation Studio, draft guidelines

## Pending (Week 1)
- [ ] Literature review with individually verified references

## Blockers / external dependencies
- **Network:** huggingface.co and unicode.org are blocked from the cloud dev workspace, so real model
  inference (Weeks 6–9) needs those domains allowed (claude.ai Settings > Capabilities) or must run on the M4 Mac.
- Human annotators (Weeks 5–8) are not yet recruited; see research/ANNOTATION_PLAN.md.
- The Gujarati Tesseract pack (`guj`) is not installed in the dev container (needed in Week 8).

## Latest verified commit
See `git log -1 origin/main`; CI must be green before a batch counts as verified.

## Next exact task
Week 6: `emojilens_core/models/`. Define the adapter interface (capabilities TOKENIZE/CLASSIFY/EMBED/
GENERATE/VISION_INPUT/OCR, metadata, lazy loading) and the SafetyJudge (response behaviour separate
from the safety judgment), with contract tests using clearly labelled fake adapters. **Real model
inference is blocked in the cloud workspace** (huggingface.co is not reachable). Either allow
huggingface.co in claude.ai Settings > Capabilities, or run model selection and downloads on the M4 Mac
after a resource check. The Tesseract adapter (eng, hin) can be built here; `guj` traineddata is
missing.

## Estimated remaining work
About 5 of 10 roadmap weeks. Weeks 1–5 met as infrastructure, except the literature review, Week 6–dependent semantic comparison and real human annotation (external).
