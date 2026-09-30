# Readability and diagrams

Use this reference when drafting or auditing root entrypoints, long guides,
workflows, architecture explanations, or Mermaid diagrams.

## Start from the reader task

Give each document one primary promise. The opening should tell the reader what
they can accomplish there and point elsewhere for broader detail. Arrange
sections in prerequisite order so the reader never needs information that is
introduced later.

Common sequences are guidance, not fixed templates:

- Quick experience: identify board and artifact, verify the bundle, flash it,
  provision and try the product, then offer source-build and deeper links.
- Architecture: establish product scope, show layers and ownership, explain
  runtime or media flows, state contracts, show extension paths, then explain
  evidence and verification.
- Contribution: prepare the environment, classify the change, read the rules
  that apply to that class, implement it, run proportional tests, update
  documentation, and complete submission checks.

Do not preserve an existing section order merely because every individual
section is accurate. A source-download chapter placed in the middle of a binary
quick-start is still a usability defect.

## Shape paragraphs and sections

Introduce context or a decision before commands, tables, or diagrams. Keep one
main idea per paragraph. Put the result, warning, or next step next to the action
it qualifies instead of collecting all caveats at the end.

Use headings for real reader tasks, not for every small fact. Keep heading
levels monotonic and avoid a deep hierarchy in root entrypoints. Lists are
useful for choices, requirements, and procedures; ordinary explanation should
remain prose rather than a stack of one-line bullets.

For Chinese, run a natural-language review after the facts and structure are
stable. Explain an unavoidable acronym on first use in each independently
readable document. Prefer direct verbs and concrete ownership over abstract
claims or slogan-like conclusions.

## Decide whether a diagram helps

A diagram is useful for at least three dependent steps, three or more branches,
layer ownership, or relationships that are hard to reconstruct from prose. Use
the smallest fitting form: flowchart for sequence or decisions, hierarchy for
ownership, and table for repeated exact mappings.

Do not add a diagram for a single command, a short list, or decoration. Root
quick-start pages should normally stay linear. Architecture and contribution
guides are better candidates because their readers compare layers, lifecycle
states, or alternative extension paths.

Prefer Mermaid in Markdown repositories that render it. Place a one- or
two-sentence reading cue immediately before the diagram. Keep labels short,
define acronyms outside the diagram, and avoid colors or styling that depend on
one theme.

The diagram must not be the only home of a safety rule, command, protocol
constant, or evidence qualification. Nearby prose owns those facts. At the same
time, do not duplicate every node as a numbered list; summarize the governing
constraint and let the diagram carry the relationship.

## Review and automate

Check heading hierarchy, prerequisite order, paragraph length, local links,
code-fence balance, and whether every diagram has an introduction and a clear
job. Render Mermaid when a renderer is already available; do not add a large
toolchain solely for a small documentation edit.

Repository tests may lock stable document roles, required destinations, and
project-specific section order. Avoid generic tests that freeze exact prose.
Tests should catch navigation drift, missing board coverage, broken links,
oversized paragraphs, duplicated volatile facts, or diagrams spreading into a
quick-start without a documented reason.
