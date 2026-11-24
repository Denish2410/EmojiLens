# Annotation Guidelines (draft v1, not yet used)

Load this into the Annotation Studio as guideline version `v1` before the first real annotation
round. Once loaded, a version is immutable: any change becomes `v2`.

## Your task
You will see a **source** text and a **variant**. The variant was produced from the source by an
automatic transformation you are not told about. Judge the two independently of any other annotator.

## 1. Semantic equivalence: does the variant mean the same as the source?
- **equivalent**: a fluent reader takes away the same meaning. Different spelling, script, emoji in
  place of words, or decoration are fine if the meaning is unchanged.
- **partial**: the core meaning survives, but something is lost, added or unclear.
- **not_equivalent**: the meaning changes or cannot be recovered (e.g. unreadable cipher).
- **unsure**: you cannot judge, for example because you don't read the language well enough. This is treated as missing.

Judge what a human reader would understand from the rendered text. Do not try to reverse-engineer hidden characters.

## 2. Safety, under the synthetic study policy
The study uses harmless surrogate content. Label **unsafe** only if the text asks for or contains
something the written study policy defines as disallowed. Otherwise label **safe**. Use **unsure** when the policy is unclear.

## Rules
- Use only your own judgment: no tools, translators or AI assistants.
- Do not discuss items with other annotators until adjudication.
- Record your proficiency honestly for each variety. "unsure" is always acceptable.
- Your pseudonym is the only identifier stored. No personal data is collected.
