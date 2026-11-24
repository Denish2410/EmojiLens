# Local Model Setup: MacBook Air M4 (Apple Silicon)

Status: **procedure prepared, not yet executed.** No model weights have been downloaded or run for
EmojiLens yet; the development workspace cannot reach huggingface.co. Until this procedure has been
run on the target machine, every real-inference acceptance criterion stays open.

## 1. Candidate models

Selection criteria: an open license, coverage of en, hi and gu where possible, a size that fits a
16 GB unified-memory laptop alongside the API, Apple Silicon (MPS) support through PyTorch, and
pinned revisions for reproducibility.

| Key | Repository | Role | Approx. disk | Approx. RAM | License (check before download) |
|---|---|---|---|---|---|
| `classifier-xlmr-sentiment` | cardiffnlp/twitter-xlm-roberta-base-sentiment | CLASSIFY (surrogate task), TOKENIZE | ~1.1 GB | ~1.5 GB | check the model card |
| `embed-multilingual-minilm` | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | EMBED, TOKENIZE | ~0.5 GB | ~1.0 GB | Apache-2.0 (check) |
| `gen-qwen2.5-0.5b-instruct` | Qwen/Qwen2.5-0.5B-Instruct | GENERATE, TOKENIZE | ~1.0 GB | ~2.5 GB | Apache-2.0 (check) |
| `vlm-smolvlm-256m` | HuggingFaceTB/SmolVLM-256M-Instruct | VISION_INPUT | ~0.6 GB | ~2.0 GB | Apache-2.0 (check) |
| `tesseract-ocr` | Tesseract 5 + eng/hin/guj traineddata | OCR | ~0.1 GB | <0.5 GB | Apache-2.0 |

Sizes are estimates for planning. The setup script checks free disk with a 2× margin before
downloading. **Licenses must be confirmed on each model card.** Record the confirmed license in
`packages/core/src/emojilens_core/models/catalog.py` before using a model in reported experiments.
The classifier is a *surrogate-task* model (sentiment), not a safety model. The SafetyJudge maps
its labels only through an explicit, documented label map in each experiment's configuration.

Total for everything above: roughly 3.3 GB of disk. Peak RAM depends on how many models are loaded
at once. The registry keeps at most `EMOJILENS_MAX_LOADED_MODELS` (default 2) loaded and unloads
the least recently used.

## 2. Install system dependencies (Homebrew)
```bash
brew install python@3.11 uv node pnpm tesseract tesseract-lang
tesseract --list-langs | grep -E '^(eng|hin|guj)$'   # all three must be listed
```

## 3. Install Python extras for models
```bash
cd EmojiLens
uv sync --all-packages --extra models --python 3.11
uv run python -c "import torch; print(torch.__version__, torch.backends.mps.is_available())"
```
`EMOJILENS_DEVICE=auto` (the default) picks MPS when it is available and otherwise falls back to
CPU. CUDA is never assumed.

## 4. Download and pin exact revisions
```bash
uv run python scripts/setup_models.py --list
uv run python scripts/setup_models.py embed-multilingual-minilm gen-qwen2.5-0.5b-instruct \
    classifier-xlmr-sentiment vlm-smolvlm-256m
cat var/model_pins.json      # commit SHAs actually downloaded
```
The script resolves each repository's current commit SHA, downloads exactly that commit and records
it. Adapters load only with `local_files_only=True`, `trust_remote_code=False` and the pinned revision.
A model that is unpinned or missing from the cache shows as *not downloaded* in the Model Arena.

## 5. Verify real inference
```bash
scripts/dev-api.sh &                       # API on 127.0.0.1:8000
uv run pytest -m "real_model or real_ocr"  # real-model tests
```
Then open the **Model Arena**. Each model should show *available*, and TOKENIZE, EMBED, CLASSIFY and
GENERATE should return results with the pinned revision in their metadata. Record the outcomes, with
the date and machine, in `docs/TEST_REPORT.md`. Only then can the Week 6 real-inference criteria be ticked.

## 6. Reproducibility record
Commit `var/model_pins.json` only if the repository owner agrees. It is git-ignored by default
because `var/` holds local state. Otherwise, copy the pins into the experiment's documentation. Every
stored model output already records the model id, revision, tokenizer revision, adapter version,
device, dtype and library versions.
