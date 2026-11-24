# Research Proposal (draft v0.1)

## Title
EmojiLens: A Cross-Model, Multilingual and Multimodal Security Intelligence Framework for
Detecting Emoji-Based Adversarial Manipulation in AI Systems.

## Problem
Humans, language models, safety classifiers, OCR engines and vision-language models can each
interpret the same emoji- or Unicode-bearing content differently. Some code points are
invisible to readers but present to tokenizers. Some substitutions keep the meaning for humans
but change it for classifiers. Rendering can collapse or reveal characters. Where these
interpretations diverge, a safety decision made on one representation may not hold for another.

## Research question
Can security failures caused by differences in how humans, AI models and AI safety systems
interpret emoji-based content be systematically measured, explained and mitigated?

## Objectives
- **O1 (Forensics):** Build a reversible, provenance-preserving Unicode inspection engine that
  separates legitimate structure (emoji sequences, Indic joiners) from anomalous or concealed content.
- **O2 (Transformations):** Implement six versioned, seeded transformation families plus an
  identity control, for reproducible defensive evaluation.
- **O3 (Measurement):** Define and validate two separate experimental metrics, CRSC-sem
  (semantic consistency) and CRSC-safe (safety-decision consistency), with group-level bootstrap CIs.
- **O4 (Coverage):** Evaluate across five language varieties (en, hi, gu, hi-Latn, gu-Latn)
  and three input paths (text, screenshot→OCR, screenshot→VLM).
- **O5 (Ground truth):** Collect human semantic-equivalence annotations with measured
  inter-annotator agreement.
- **O6 (Defence):** Build EmojiGuard, an explainable rule-based and learned detector, and
  compare it with simple baselines through ablations, explicitly measuring false positives on
  legitimate emoji and Indic text.

## Hypotheses (to be finalized before any experiments run)
- **H1:** For at least one model, CRSC-safe for meaning-preserving variants is lower than for
  identity controls (more label flips).
- **H2:** CRSC-sem agrees with human equivalence labels better than lexical similarity does.
- **H3:** EmojiGuard reaches higher recall than the strip-invisibles and NFKC baselines at a
  false-positive rate on benign Indic and emoji controls that is no worse than theirs.

Thresholds, test statistics and stopping rules will go in the statistical analysis plan
(Week 7) before final experiments.

## Novelty
No claim of being "first" is made. Contributions will be stated against a literature review
whose references have been individually verified (pending, see `LITERATURE_REVIEW.md`).

## Known constraints
- Gujarati and Romanized Gujarati resources are scarce. This will be documented as a limitation.
- Human annotation depends on recruiting bilingual annotators (an external dependency).
- Only small local models fit on the target hardware (Apple Silicon, M4 MacBook Air).
