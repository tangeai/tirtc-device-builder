# Document architecture

Use this reference when deciding where information belongs or when a repository
has accumulated duplicate guides.

## Entry hierarchy

The root is a small set of durable entrypoints:

| Document | Reader question | Content boundary |
| --- | --- | --- |
| `README.md` | How do I run this now? | Board choice, release download, safe flashing, provisioning, first experience |
| `ARCHITECTURE.md` | How does it work and where do I extend it? | Product flows, module interfaces, data/lifecycle paths, repository responsibilities |
| `CONTRIBUTING.md` | How do I make and verify a change? | Environment, tests, evidence, board/platform intake, submission checks |
| `docs/README.md` | Where is the complete documentation? | Task-oriented index to product, development, board, test, and reference material |

Do not turn the root README into a complete hardware manual. It may show a
compact card or table for a small set of primary boards. Each row links to the
release artifact and the board's full guide. As the catalog grows, keep only the
primary boards in the root and link the complete catalog.

## Detail ownership

- `docs/product/` owns current user-visible behavior, interaction, protocols,
  and media contracts.
- `docs/development/` owns architecture details, toolchains, builds, tests,
  porting, release mechanics, and AI-assisted development.
- `docs/boards/<board-id>/` owns model-specific specifications, dependencies,
  schematics, build/flash steps, first use, verification, and limitations.
- `boards/<vendor>/<board>/` owns build-participating board facts and a short
  pointer README when the repository uses this layout.
- `references/` indexes external SDKs, schematics, examples, and datasheets that
  are inputs rather than maintained product documentation.
- Local ignored history owns dated investigations and superseded status
  snapshots. Public documents state only current behavior and current limits.

## Root navigation

Place navigation immediately after the title or language selector. Keep it
short and identical across public root documents. A typical Chinese set is:

```markdown
[快速体验](README.md) · [架构与二次开发](ARCHITECTURE.md) ·
[参与开发](CONTRIBUTING.md) · [完整文档](docs/README.md)
```

Add language links only when the target files exist and have passed review.
Do not publish dead “English coming soon” links.

## Single-source rule

Summaries may repeat a conclusion, but volatile values have one owner. Board
memory, SDK version, stream identifiers, sample rates, checksums, and build
commands should be read from manifests, contracts, lock files, release
metadata, or their designated documentation owner. Other pages link there.

When duplication is unavoidable for a quick-start step, keep the detailed page
authoritative and add a test that detects drift in the copied value.
