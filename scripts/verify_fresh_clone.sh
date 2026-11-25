#!/usr/bin/env bash
# Verify that a fresh clone of the committed tree builds and passes every gate.
# Clones HEAD (committed files only, so ignored or uncommitted files cannot mask a problem)
# into a temporary directory and runs the documented gates there.
#
#   scripts/verify_fresh_clone.sh            # Python + web gates
#   E2E=1 scripts/verify_fresh_clone.sh      # also Playwright (needs Chromium; see CLAUDE.md)
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
git clone --quiet --no-hardlinks "$SRC" "$WORK/repo"
cd "$WORK/repo"
echo "fresh clone of $(git rev-parse --short HEAD)"
uv sync --all-packages --frozen --python 3.11 --quiet
uv run ruff check . && uv run ruff format --check .
uv run mypy packages/core/src apps/api/src packages/core/tests apps/api/tests scripts
uv run python scripts/freeze_configs.py check
uv run pytest -q -m "not real_model"
pnpm install --frozen-lockfile --silent
pnpm web:typecheck && pnpm web:lint && pnpm web:test && pnpm web:build
if [[ "${E2E:-0}" == "1" ]]; then
  pnpm --filter @emojilens/web exec playwright test
fi
echo "fresh-clone verification passed"
