# Changelog

All notable changes are documented here. Format based on Keep a Changelog.

## [Unreleased]
### Added
- Week 2 Unicode forensics: contextual evidence classifier (5 categories, ruleset 0.2.0), legitimate
  emoji/Indic/Arabic structure recognition, mixed-script and whole-script homoglyph detection,
  tag-ASCII and variation-selector byte decoders, reversible derived views, Inspector evidence and
  view panels.
- `scripts/source_hygiene.py` and a repository test that rejects raw invisible or confusable characters
  in source code.
### Fixed
- Raw invisible characters in test fixtures and the Inspector sample are now written as escapes.
- Vitest no longer collects Playwright specs.
- Monorepo foundation (uv and pnpm workspaces), project rules and memory files.
- `emojilens_core.unicode`: input validation (`invalid_unicode`), SHA-256 of the original UTF-8,
  grapheme segmentation, code point inspection, and code point / UTF-8 / UTF-16 offset mapping.
- API v1: `/health`, `/ready`, `POST /unicode/analyze`; structured errors; input size limit.
- Database foundation M0 (SQLite WAL, Alembic).
- Web console shell with Overview and Unicode Inspector; dark and light themes; mobile drawer.
- CI workflow; Vitest, Pytest/Hypothesis and Playwright test suites.
