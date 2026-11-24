# Test Report

## 2026-11-24: Week 1 foundation

**Environment:** Linux x86_64 dev container, Python 3.11 (uv 0.11), Node 22, pnpm 10.28,
Google Chrome for Testing 153 (Playwright). The primary target, an Apple Silicon M4, has not been verified yet.

| Suite | Command | Result |
|---|---|---|
| Ruff lint + format | `uv run ruff check . && uv run ruff format --check .` | pass |
| mypy (strict) | `uv run mypy packages/core/src apps/api/src packages/core/tests apps/api/tests` | pass, 23 files |
| Pytest + Hypothesis | `uv run pytest` | **36 passed** (23 core, 13 API) |
| TypeScript | `pnpm web:typecheck` | pass |
| ESLint | `pnpm web:lint` | 0 errors, 2 warnings (react-refresh export hints on provider hooks) |
| Vitest + RTL + MSW | `pnpm web:test` | **11 passed** |
| Production build | `pnpm web:build` | pass (JS 99.6 kB gzip) |
| Playwright E2E (real API, no mocks) | `playwright test` | **4 passed** (desktop + Pixel 7 × 2 specs) |

**What is covered**
- Core: hash equals sha256(utf-8) (property test); lone surrogates are rejected with their offset; graphemes reconstruct the input (property test);
  spans match Python's UTF-8 and UTF-16 encoders (property test); UTF-16 round trip; offsets inside a surrogate pair are rejected; ZWJ family, skin tone, keycap,
  national and subdivision flags, and VS16 heart each form a single grapheme; Devanagari ZWJ and Gujarati ZWNJ are preserved.
- API: exact preservation and hashing; UTF-16 spans for astral characters; `invalid_unicode` returned over HTTP; 413 size limit;
  structured 422 and 404 errors; OpenAPI; liveness; readiness (ready and not-ready cases); fresh migration with WAL and FK pragmas; downgrade and re-upgrade.
- Web: live status, empty state, error state, theme persistence, mobile drawer (open, navigate, Escape), 404 page,
  exact input sent to the API, rendering of analysis data, grapheme→code point highlighting, structured error display.
  MSW mocks are used only in these unit tests.
- E2E: the real API and browser together; the SHA-256 shown in the UI matches a Node-computed hash of the input.

**Known gaps**
- The CI workflow has not run on GitHub yet (no remote at the time of testing).
- Headless Chrome in this container lacks Indic fonts, so Devanagari and Gujarati render as fallback glyphs in screenshots.
  The data path is correct. Font provisioning is tracked for Week 2 and Week 8.
- No accessibility audit tool (such as axe) is wired in yet.
