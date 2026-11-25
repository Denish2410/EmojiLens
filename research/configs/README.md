# Frozen research configurations

- `templates/`: starting points. These are never frozen or run as-is.
- `*.json` in this folder: experiment configs. Each is checked with
  `scripts/freeze_configs.py validate` against the API schema, and a label map is accepted only for
  safety-task models.
- `LOCK.json`: SHA-256 digests of frozen files (configs and `research/ANALYSIS_PLAN.md`).
  `scripts/freeze_configs.py check` runs in CI and fails if a frozen file changes. Edits to a frozen
  file are not allowed: add a new file and log the deviation in the analysis plan.

No config is frozen yet. The analysis plan is still a draft (`research/READINESS.md`, item 6).
