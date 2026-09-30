---
name: tirtc-project-docs
description: Design, audit, and maintain bilingual documentation systems for TiRTC or XiaoTai multi-board firmware repositories. Use for quick-start READMEs, architecture and contribution guides, board catalogs, build/flash instructions, media parameters, navigation/link checks, or Chinese-to-English synchronization; exclude code-only work and historical status logs.
---

# TiRTC Project Documentation

Build a documentation system that lets a first-time user run the product, lets
a developer extend it, and gives an agent reliable pointers into repository
truth. Documentation describes the current product and supported workflows;
dated investigations and migration diaries belong in an ignored local history
area when the repository defines one.

## Establish the contract

1. Read repository guidance such as `AGENTS.md`, the existing documentation
   index, glossary, documentation contract, board architecture, and build/test
   entrypoints. Project rules override this Skill.
2. Inventory existing public documents before adding files. Preserve useful
   paths and repair their role when possible; do not create a parallel document
   tree for the same audience.
3. Identify the requested phase: Chinese drafting, Chinese review, English
   synchronization, or audit. When the user requests Chinese approval first,
   stop after the verified Chinese result. Do not create English placeholders.
4. Map every technical claim to a source. Read
   [evidence and technical claims](references/evidence.md) when the work covers
   hardware, media, tools, builds, releases, or validation status.
5. State the primary reader task for every entry document before drafting its
   sections. Read [readability and diagrams](references/readability-and-diagrams.md)
   for root entrypoints, long guides, workflow documents, or any proposed
   visualization.

## Select the document layer

Read [document architecture](references/document-architecture.md) when adding,
splitting, renaming, or reorganizing documents.

- Root `README.md` is the quick-experience path: identify the board, download
  the matching release artifact, flash it safely, provision it, and try the
  principal product flows.
- Root `ARCHITECTURE.md` explains product capabilities, module interfaces,
  runtime/media flows, repository responsibilities, and secondary-development
  entrypoints for both humans and agents.
- Root `CONTRIBUTING.md` explains environment setup, tests, evidence, adding a
  board or platform, and the submission workflow.
- `docs/README.md` is the complete task-oriented index.
- `docs/boards/README.md` catalogs every board; each board has one independently
  usable guide under `docs/boards/<board-id>/README.md`.
- Product, development, and board details stay in their subject directories.
  Root documents summarize and link instead of copying those details.

Keep a compact navigation line at the top of every public root document. Every
link must resolve from that file, and all root documents must expose the same
destinations in the same order.

## Draft from repository truth

Write the minimum information needed at the selected layer. Prefer stable
interfaces, responsibilities, commands, and decision points over source-tree
tourism. Explain an unavoidable acronym on first use. Keep one topic per
paragraph and make commands, warnings, status, and next actions easy to scan.

Order sections by the reader's next decision, not by the order in which facts
were discovered. A quick-start normally moves from board/artifact choice to
flashing, first experience, and only then source development. An architecture
guide moves from product scope to layers, runtime flows, contracts, extension,
and verification. A contribution guide moves from prerequisites to change
classification, applicable constraints, tests, and submission.

Use a diagram only when it makes a multi-step flow, hierarchy, or branching
decision materially easier to understand. Keep it small, introduce it in prose,
and retain critical constraints in nearby text. Do not repeat the same complete
sequence as both a numbered list and a diagram. Keep complex architecture out
of the quick-start README unless it is necessary to complete the first run.

Use available specialist Skills when they materially apply:

- `research` for facts that require official external sources and citations;
- `codebase-design` for module interfaces, seams, adapters, and extension paths;
- `domain-modeling` when canonical terms are missing or conflict;
- `writing-for-agents` for `AGENTS.md`, Skill instructions, and agent-facing
  pointers;
- `humanizer-zh` as the final Chinese prose review after facts are stable.

Their absence must not block ordinary maintenance. Preserve the same outcomes:
primary sources, explicit interfaces, consistent terms, actionable pointers,
and natural restrained Chinese.

## Verify before translation

Check every changed command against current scripts or `--help`, every local
link against the filesystem, every board identifier against its manifest, and
every download/flash instruction against the release artifact manifest. Run the
repository's documentation, manifest, and host-test gates. A passing structure
test does not upgrade build evidence into hardware proof.

Review the Chinese documents for facts, terminology, navigation, paragraph
shape, section order, diagram purpose, and duplicated sources of truth. Present
the Chinese result for approval when requested. Completion for this phase means
all requested Chinese documents and checks are complete, with English files
still untouched.

## Synchronize English after approval

Read [bilingual synchronization](references/bilingual.md) only after the
Chinese source has been approved. Translate meaning rather than sentence order,
preserve commands and identifiers exactly, rebuild relative navigation for the
English files, and rerun the same checks. Record intentional locale differences
instead of silently dropping Chinese-only instructions.

## Report the result

List the documents created or changed, the sources used for claims, checks run,
and unresolved evidence gaps. Separate missing documentation from unsupported
features. Do not present an unverified artifact, inferred pin map, or stale test
result as a current product capability.
