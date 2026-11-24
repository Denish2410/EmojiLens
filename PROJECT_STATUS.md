# Project Status

**Current week:** 4 (Transformation engine)
**Current milestone:** Weeks 2–3 are complete. Outstanding: the Week 1 literature review and multilingual semantic comparison (needs Week 6 embeddings).
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
Week 4: `emojilens_core/transforms/`. Start with the transformation interface (id, version, seed, config,
provenance, offset map, validation) and the identity transform, then the six families, followed by the M2
variants migration.

## Estimated remaining work
About 7 of 10 roadmap weeks. Weeks 1–3 met except the literature review and Week 6–dependent semantic comparison.
