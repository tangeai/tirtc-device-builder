# Bilingual synchronization

Use this reference only after the project owner has approved the Chinese source.

## File policy

Keep Chinese as the source language unless the repository declares another
policy. Use stable English siblings such as `README.en.md`,
`ARCHITECTURE.en.md`, and `CONTRIBUTING.en.md`. Subject documents may use the
same suffix convention or separate language trees, but one repository should
use one convention.

Add language selectors only after both targets exist. The Chinese root
navigation points to Chinese destinations; the English navigation points to
English destinations where available and to a clearly labelled Chinese page
only when no English counterpart exists.

## Translation rules

- Preserve commands, paths, board IDs, artifact names, checksums, log fragments,
  configuration keys, and protocol constants exactly.
- Use official English vendor and product names. Do not translate identifiers.
- Translate the meaning and reader task, not Chinese word order.
- Keep warnings, evidence qualifications, limitations, and follow-up items at
  the same strength as the Chinese source.
- Explain acronyms on first use in each independently readable document.
- Recheck relative links because an English sibling can have different targets.

## Drift review

Compare section coverage rather than raw line count. Every Chinese section must
have an English counterpart or a recorded locale-specific reason. Verify tables
row by row, then rerun link, manifest, documentation, and host-test gates.

Translation is complete when the English reader can perform the same supported
task and sees the same capability and evidence status as the approved Chinese
reader.
