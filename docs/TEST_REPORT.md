# Test Report

## 2026-11-24: Week 3 multilingual and datasets

| Suite | Result |
|---|---|
| Ruff, mypy strict, source hygiene | pass |
| Pytest + Hypothesis | **158 passed** (core incl. 29 benign-fixture cases, API 25, repo 2) |
| TypeScript, ESLint (0 errors), Vitest | pass, **21 passed** |
| Production build | pass |
| Playwright E2E (real API) | **10 passed** (5 specs × desktop/mobile) |

Observed on the synthetic benign fixture (28 records; synthetic, not research data): declared vs.
heuristic language agree 23, disagree 4, undetected 1. With seed 20261124, the split was train 19,
validation 5, test 4, and there was no leakage.


## 2026-11-24: Week 2 Unicode forensics

Same environment as below. All gates were run and judged by exit code:

| Suite | Result |
|---|---|
| Ruff lint + format, mypy strict (31 files) | pass |
| Pytest + Hypothesis | **90 passed** (core 75, API 14, repo hygiene 2) |
| Source hygiene check | pass (no raw invisible/confusable characters) |
| TypeScript, ESLint | pass (ESLint: 0 errors, 3 react-refresh warnings) |
| Vitest | **16 passed** (2 files) |
| Production build | pass |
| Playwright E2E (real API) | **6 passed** (3 specs × desktop/mobile) |
| GitHub Actions | see the run for the pushed commit |

New coverage: benign multilingual and emoji controls stay at or below informational; all six RGI
sequence subtypes; Devanagari and Gujarati ZWJ/ZWNJ after a virama; ZWSP splitting a word versus
standing alone; out-of-context ZWJ; bidi controls without RTL text, unbalanced, and balanced isolates in
RTL text; styled mathematical letters; mixed-script look-alike words with exact spans; tag and
variation-selector payload decoding; undecodable variation-selector runs; property tests for view
tiling and normalization equality; an API contract test; UI tests (ordering, inert payload rendering,
cross-panel selection, view tabs); E2E covering a concealed tag payload alongside a legitimate Gujarati ZWNJ.


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
| Vitest + RTL + MSW | `pnpm web:test` | **11 passed**; see the correction below |
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

**Correction (CI run #1, 2026-11-24):** the Vitest command above actually exited non-zero.
Vitest also collected `e2e/inspector.spec.ts` (a Playwright spec) and failed to load it,
even though all 11 unit tests passed. The local check filtered output to the test count and
missed the file-level failure. The fix limits Vitest to `src/**/*.test.{ts,tsx}`. Gates are now
verified by exit code, not by filtered output.

**Known gaps**
- Headless Chrome in this container lacks Indic fonts, so Devanagari and Gujarati render as fallback glyphs in screenshots.
  The data path is correct. Font provisioning is tracked for Week 2 and Week 8.
- No accessibility audit tool (such as axe) is wired in yet.
