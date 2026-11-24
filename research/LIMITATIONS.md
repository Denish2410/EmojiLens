# Known Limitations (living document)

This file is updated as limitations are found. Every reported result must be read with these in mind.

## Language identification (Week 3)
- Variety identification (`script+lexicon/0.1.0`) is a transparent heuristic baseline built on
  hand-curated seed lexicons. It has not been validated against labelled data. Declared and detected
  languages are stored side by side, and disagreement is reported rather than hidden: on the synthetic
  benign fixture, 23 of 28 agree, 4 disagree and 1 is undetected.
- Romanized Hindi and Romanized Gujarati have no standard spelling and share many function words
  ("to", "ke", "na"). Those tokens are counted fractionally across both varieties, not resolved.
- **Romanized Gujarati (gu-Latn)** has the smallest lexicon and the least public data, and CLDR
  has no gu-Latn locale. Its emoji meanings fall back to Gujarati, then English, and every fallback is flagged.

## Unicode data versions
- Python 3.11's `unicodedata` is at Unicode 14.0. The `regex` grapheme segmentation and the
  `emoji` package (2.16) are newer. Emoji added after Unicode 14 may get names from `emoji` but
  categories from 14.0. All versions are reported with every analysis.
- Confusables come from the `confusable_homoglyphs` 3.3.1 snapshot, which is older than
  current Unicode, so newer look-alikes may be missed (D-009).

## Fixtures versus research data
- `datasets/fixtures/benign_controls.synthetic.jsonl` was written by the developers for testing.
  It is a synthetic fixture, not a sample of real-world usage, and is never included in research results.

## Environment
- The cloud development workspace cannot reach huggingface.co or unicode.org. Model-based work
  (Weeks 6–9) needs those hosts allowed or must run on the target Apple Silicon machine.
