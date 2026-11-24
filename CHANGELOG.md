# Changelog

All notable changes are documented here. Format based on Keep a Changelog.

## [Unreleased]
### Added
- Monorepo foundation (uv and pnpm workspaces), project rules and memory files.
- `emojilens_core.unicode`: input validation (`invalid_unicode`), SHA-256 of the original UTF-8,
  grapheme segmentation, code point inspection, and code point / UTF-8 / UTF-16 offset mapping.
- API v1: `/health`, `/ready`, `POST /unicode/analyze`; structured errors; input size limit.
- Database foundation M0 (SQLite WAL, Alembic).
- Web console shell with Overview and Unicode Inspector; dark and light themes; mobile drawer.
- CI workflow; Vitest, Pytest/Hypothesis and Playwright test suites.
