# EmojiLens

**A cross-model, multilingual and multimodal security intelligence framework for detecting
emoji-based adversarial manipulation in AI systems.**

*See what AI sees. Detect what humans miss.*

> Status: early development (Week 1, Foundation). See [PROJECT_STATUS.md](PROJECT_STATUS.md)
> and [ROADMAP.md](ROADMAP.md). No research results exist yet.

## Research question
Can security failures that arise when humans, AI models and AI safety systems interpret
emoji-based content differently be systematically measured, explained and mitigated?

## What works today
- **Unicode analysis engine** (`packages/core`): exact-input SHA-256, extended grapheme
  clusters, per-code-point names, categories and UTF-8 bytes, code point / UTF-8 / UTF-16
  offset spans, and descriptive markers for invisible and structural code points.
- **API** (`apps/api`): `POST /api/v1/unicode/analyze`, `GET /api/v1/health` and
  `GET /api/v1/ready`. Interactive docs are at `/api/v1/docs`.
- **Web console** (`apps/web`): Overview (live system status) and Unicode Inspector.

## Quick start
Requirements: Python 3.11, [uv](https://docs.astral.sh/uv/), Node 22 and pnpm 10.

```bash
uv sync --all-packages --python 3.11
pnpm install
scripts/dev-api.sh          # migrates the DB, serves http://127.0.0.1:8000
pnpm web:dev                # http://127.0.0.1:5173 (proxies /api to the API)
```

## Tests
```bash
uv run ruff check . && uv run mypy packages/core/src apps/api/src && uv run pytest
pnpm web:typecheck && pnpm web:lint && pnpm web:test && pnpm web:build
pnpm --filter @emojilens/web exec playwright test   # real API + browser
```

## Layout
```
apps/api        FastAPI service, Alembic migrations
apps/web        React console
packages/core   emojilens_core research engine
research/       objectives, threat model, methodology
docs/           decisions, test reports
scripts/        developer scripts
```

## Responsible use
EmojiLens is a defensive research tool. It uses harmless surrogate tasks and synthetic
policies, and it does not test public AI services. See [SECURITY.md](SECURITY.md).
