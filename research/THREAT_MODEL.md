# Threat Model (draft v0.1)

## System under study
An AI pipeline in which text, or a rendered image of text, passes through one or more of:
a safety classifier, a tokenizer and language model, OCR, and a vision-language model.

## Adversary (studied, not enabled)
- **Goal:** content judged unsafe in its plain form is judged safe after transformation (or
  the reverse: benign content gets blocked), while a human still reads the intended meaning.
- **Capabilities:** full control over the input string. Inserts invisible or format code points,
  variation selectors and tag characters; substitutes emoji for words; uses homoglyphs and mixed
  scripts; obfuscates; mixes languages and scripts.
- **Not assumed:** access to model weights, training data or the deployment infrastructure.

## Representations where divergence can occur
1. Human visual reading of the rendered text.
2. Code point sequence (as tokenizers and classifiers see it).
3. Normalized views (NFC/NFKC), which can merge or split characters.
4. Sanitized views, which may delete content that carries meaning.
5. OCR output of the rendered image.
6. VLM interpretation of the rendered image.

## Assets
Accuracy of safety decisions; integrity of the original input and its evidence;
reproducibility of research results.

## Defender (EmojiLens and EmojiGuard)
Inspects all representations, reports evidence with exact locations, and recommends an action.
It must not penalize legitimate emoji use, Indic joiners or code-mixed language.

## Threats to EmojiLens itself
| Threat | Mitigation |
|---|---|
| Executing dataset or model content | Content is data only; no eval or shell; React escapes all text |
| Prompt injection inside samples or papers | Instructions in content are never followed; no autonomous tool use on content |
| Resource exhaustion through huge inputs | Code point limit per request (413 `input_too_large`); bounded inference |
| Malformed Unicode crashing analysis | Strict validation (`invalid_unicode`), property-based tests |
| Malicious HTML in the screenshot renderer | Text-only rendering, sandboxed, external loads blocked (Week 8) |
| Untrusted model code | `trust_remote_code=False`; pinned revisions |
| Path traversal through uploads | Path validation on import (Week 3) |
| Error responses leaking data | Errors never echo submitted input |

## Out of scope
Attacking public AI services, credential extraction, producing real harmful payloads.
