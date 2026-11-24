# Project Status

**Current week:** 1 (Foundation)
**Current milestone:** Week 1 is nearly complete. Only the literature review is outstanding.
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

## Pending (Week 1)
- [ ] Literature review with individually verified references

## Blockers / external dependencies
- Human annotators (Weeks 5–8) are not yet recruited.
- The Gujarati Tesseract pack (`guj`) is not installed in the dev container (needed in Week 8).

## Latest verified commit
`2e79a3c` on `origin/main` (Denish2410/EmojiLens), CI green.

## Next exact task
Week 2: implement the contextual evidence classifier in `emojilens_core/unicode/evidence.py`,
starting with recognition of legitimate structures (RGI emoji ZWJ sequences, VS16/VS15, modifiers,
keycaps, subdivision flags, and ZWJ/ZWNJ after a Devanagari or Gujarati virama). Write the tests first.

## Estimated remaining work
About 9 of 10 roadmap weeks. Week 1 acceptance criteria: 9 of 10 met (literature review outstanding).
