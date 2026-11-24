# Human Annotation Plan (draft v0.1, recruitment preparation)

Status: **no annotators recruited yet.** This is an external dependency. No annotation data exists,
and none will be simulated.

## Goal
Collect human judgments of whether a transformed variant keeps the meaning of its source, as ground
truth for validating CRSC-sem. Safety labels are collected separately.

## Target
- About 100–150 source/variant pairs, stratified by language variety (en, hi, gu, hi-Latn, gu-Latn)
  and transformation family, plus identity controls as attention checks.
- At least two independent annotators per pair on a stratified subset; agreement reported with
  Cohen's kappa (two annotators) and Krippendorff's alpha (more than two, or missing labels).

## Annotator profile
- Fluent readers of the variety they annotate. Gujarati and Romanized Gujarati need native or
  near-native Gujarati readers, which are expected to be the hardest to recruit.
- Proficiency is self-reported per variety (none, basic, fluent, native) and stored with each
  annotation.

## Labels
- Semantic equivalence: `equivalent`, `partial`, `not_equivalent`, `unsure`.
- Safety (separate pass): `safe`, `unsafe`, `unsure` under a written synthetic policy.

## Procedure
1. Versioned guidelines, with worked examples written before any data is shown.
2. Blinded queues: annotators do not see the transformation family, the model outputs or other annotators' labels.
3. A calibration round on fixture pairs, which is excluded from analysis.
4. Disagreements go to adjudication. Both the raw and adjudicated labels are kept.

## Ethics
- Use synthetic, non-harmful content only. Do not collect personal data beyond a pseudonymous
  annotator ID and language proficiency. Participation is voluntary, and annotators may stop at any time.

## Recruitment options (for the project owner)
- Classmates or colleagues fluent in Hindi or Gujarati, with a short consent note.
- A university language department or student group.
