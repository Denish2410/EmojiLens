# Transformation Taxonomy (v1, engine transforms 1.0.0)

Every transformation is versioned and seeded. It records provenance and a piece map back to
original offsets, and it is validated on every application. Transformations run only locally, on
harmless surrogate tasks, for defensive evaluation. Concealed payloads are caller-supplied surrogate
text (default `SURROGATE-TOKEN`).

| Family | Transform id | Techniques | Varieties | Human-visible change | Reversible | Detected by (Week 2 evidence rules) |
|---|---|---|---|---|---|---|
| Control | `identity` | none | all | none | yes | none expected (a finding here is a false positive) |
| 1. Unicode smuggling | `unicode_smuggling` | zero-width word splits (ZWSP/ZWNJ/WJ); tag-character ASCII payload; variation-selector byte payload; bidi-override word reversal | all | none or almost none | yes (decoders) for splits and payloads | `zero_width.inside_word`, `tag.ascii_payload`, `variation_selector.byte_payload`, `bidi.control_without_rtl` |
| 2. Emoji substitution | `emoji_substitution` | word → emoji by CLDR name or keyword in the text's own locale | en, hi, gu, hi-Latn | yes, meaning-bearing | no | none: legitimate emoji are indistinguishable by design. Measured by CRSC instead |
| 3. Emoji cipher | `emoji_cipher` | keyed letter→emoji; regional-indicator letters (ZWNJ-separated so no flags fuse); squared letters | en, hi-Latn, gu-Latn | yes: unreadable without the key | yes, up to case | partly: heavy emoji density alone is benign. Requires semantic or model analysis |
| 4. Homoglyph | `homoglyph` | Latin → Cyrillic/Greek look-alikes; Devanagari ↔ Gujarati look-alike marks and digits | all | barely: look-alikes | no (swaps are recorded in provenance) | `homoglyph.mixed_script_word`, `homoglyph.whole_script_confusable`, `script.mixed_word` |
| 5. Text obfuscation | `text_obfuscation` | leetspeak; mathematical bold or monospace; fullwidth; case noise; separator insertion; character repetition | en, hi-Latn, gu-Latn | yes: stylistic | no | `compat.styled_letters` (styled and fullwidth only); others need normalization or models |
| 6. Code-mixing | `code_mixing` | concept-lexicon word swaps into another variety (25 concepts, v0.1) | all | yes: natural-looking mixing | no | none by design. Code-mixing is legitimate and must not be flagged |

## Design rules
- **Determinism:** each step's RNG is seeded with `"{seed}:{id}:{version}"`. A chain step `i` gets
  the derived seed `seed*1000+i`. The same inputs produce identical outputs, provenance and chain hash.
- **Offset maps:** each step returns pieces `(orig_start, orig_end, output_text)` that tile the
  input. Chains compose piece maps (`compose`), and property tests verify tiling for arbitrary chains.
- **Validation:** checks for well-formed output, tiling of the input, change from the input
  (identity must be unchanged), and a decoded round trip where a decoder exists. Unsupported
  varieties and no-op applications are reported as notes, never silently skipped.
- **Recipes:** the hash used for dataset variants covers the seed, step ids, versions and *resolved*
  parameters, so the same recipe on the same source is generated only once.
- **Leakage:** variants are generated only for frozen versions and inherit their source's split.

## Known limitations
- Emoji substitution is unavailable for gu-Latn (no CLDR locale), so the result is a no-op with a note.
- The code-mixing lexicon is small, has not been reviewed by native speakers, and uses one
  romanization per word.
- Homoglyph coverage is bounded by an older confusables snapshot (D-009).
- In a chain, a later step still uses the declared variety of the original text, so substitution
  after code-mixing only matches words left in that variety.
