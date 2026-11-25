# M4 validation workflow

This is how to establish, on the MacBook Air M4, that each model really executes, and how to record
it. Run it after `docs/MODEL_SETUP_M4.md`. The workflow verifies engineering: it shows that inference
runs. It produces no research results.

## 1. Preflight

```bash
uv run python scripts/preflight.py --network --json var/preflight.json
```

| Check | Required | Passes when |
|---|---|---|
| python | yes | Python ≥ 3.11 |
| apple_silicon | no | Darwin arm64 (warns elsewhere) |
| torch | yes | installed; MPS available on Apple Silicon (otherwise a warning) |
| transformers, sentence_transformers, huggingface_hub | yes | installed (`--extra models`) |
| disk | yes | ≥ 10 GB free (warn 5–10, fail < 5) |
| ram | no | ≥ 4 GB available; reported as *skip* on macOS, where it cannot be read without guessing |
| tesseract | yes | on PATH; warns if the `eng`, `hin` or `guj` pack is missing |
| playwright | yes | renderer importable |
| model_pins | no | `var/model_pins.json` has at least one pinned revision |
| git | no | clean checkout (warns on uncommitted changes) |
| huggingface.co | yes, with `--network` | the host answers one HEAD request |

The exit status is 0 (pass), 1 (warnings) or 2 (a required check failed). The JSON contains versions,
booleans and coarse hardware facts only. It holds no paths, user names or hostnames, so it can be
shared.

## 2. Smoke validation

```bash
uv run python scripts/validate_models.py            # every catalogue model
uv run python scripts/validate_models.py --device mps embed-multilingual-minilm
```

For each model, every declared capability runs twice on one harmless probe per variety (en, hi, gu,
hi-Latn, gu-Latn). OCR and VLM probes are rendered first in the sandboxed renderer. Each probe records:

- `executed`, `failed` (with its structured error code) or `skipped` (with the registry's reason).
  An uninstalled model is always `skipped` and never counted as passing.
- Latency, a SHA-256 of the full output, and whether both runs produced the same output (`deterministic`).
- Whether the model declares the probe's language (`yes`, `no` or `unknown`).
- For OCR and VLM: the grapheme error rate (GER) of the read-back against the visible probe, and an
  exact-match flag.

Output goes to `var/validation/<UTC stamp>/report.md` and `validation.json`. The exit status is 0 only
if at least one probe executed and none failed.

## 3. Real-model tests

```bash
uv run pytest -m "real_model or real_ocr"
```

## 4. Recording

1. Read `report.md`. Investigate any `failed` or non-deterministic probe before you record anything.
2. Add a dated entry to `docs/TEST_REPORT.md` with the machine, the preflight result and the model
   summary table copied from the report.
3. Update `PROJECT_STATUS.md`: move a model to **Real-model verified** only if all its probes executed
   on the M4.
4. Do not commit `var/`, which is local state. Attach the report to the PR or copy its tables instead.

## Interpreting the results

- Determinism: CPU inference should be bit-identical across both runs. On MPS, small floating-point
  differences can change embedding hashes. Record a mismatch as a finding; it is not a failure.
- Language coverage: an output with `declared = no` is valid data about an unsupported language. It is
  not an error.
- OCR GER on the probes includes the emoji, which Tesseract cannot read. The GER floor is therefore above
  zero even for a perfect text reading.
