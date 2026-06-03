# ANTMA

AI-Native Team Memory Architecture.

ANTMA is a local-first Python library for teams that run AI agents and need a
clear boundary between agent operating memory and reusable knowledge.

It is deliberately small. ANTMA is a memory architecture layer: it helps teams
keep raw logs, durable memory, source-of-truth notes, promotion candidates,
evidence packets, and knowledge bank entries separate while still making them
searchable and usable.

## Why ANTMA

AI teams often collect chat logs, notes, research, decisions, and project state
in one large retrieval pile. That creates three problems:

- Agents cannot tell current truth from old context.
- Humans cannot easily review or edit memory.
- Search backends become hidden sources of truth.

ANTMA starts from the opposite rule:

> Multiple memory backends are allowed, but there is only one canonical memory
> ledger.

The canonical ledger is local, human-readable Markdown. Optional indexes and
adapters are derived views.

## Core Ideas

- Agent operating memory is for state, decisions, roles, preferences, and work.
- Knowledge bank content is for reusable research, examples, frameworks, and
  reference material.
- Source-of-truth documents outrank general memory and search results.
- Promotion candidates are pending evidence, not durable truth.
- Evidence packets make completion claims auditable.
- External backends may support search or analysis, but they do not own truth.

## Scope

ANTMA owns the public-safe core of team memory:

- canonical memory ledger shape
- workspace layout and manifest
- recall priority rules
- privacy scanning guardrails
- promotion candidates for reviewed memory changes
- evidence packets for auditable completion claims
- local derived search indexes

ANTMA intentionally does not include:

- agent runtime or execution loops
- chat, email, or delivery automation
- scheduler or cron systems
- agent routing, model orchestration, or persona management
- organization-specific operating rules, names, or workflows
- hosted memory services
- automatic promotion or dreaming loops

## Install From Source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

For local checkout, editable developer install, Git URL install, and first-run
checks, see `INSTALL.md`.

## Documentation

- `INSTALL.md`: local checkout, editable, and Git URL install paths.
- `docs/tutorial.md`: first workspace, evidence, promotion, scan, index, and
  search workflow.
- `docs/api-reference.md`: CLI and Python API reference.
- `docs/privacy-boundary.md`: public-release privacy rules.
- `docs/public-release-checklist.md`: manual checks before sharing the repo.
- `docs/live/CURRENT-STATE.md`: current public-safe project state.
- `docs/live/NEXT-STEPS.md`: release and maintenance next actions.
- `docs/pypi-release.md`: PyPI release preparation.
- `CHANGELOG.md`: release and scaffold milestones.
- `CONTRIBUTING.md`: contribution workflow and review checklist.
- `SECURITY.md`: vulnerability reporting and privacy-review guidance.
- `examples/product-team-memory/`: richer synthetic product-team workspace.

## Quick Start

Create a local memory workspace:

```bash
antma init ./team-memory
```

Scan a workspace before sharing or publishing:

```bash
antma sanitize ./team-memory
```

Create a reviewable promotion candidate and evidence packet:

```bash
antma promote ./team-memory/daily/example.md --reason "Candidate durable fact."
antma evidence --objective "Public release check" --status pass \
  --criterion "tests pass" --evidence "pytest=pass=all tests passed" \
  --output ./team-memory/evidence/release-check.md
```

Build a local SQLite FTS index and search it:

```bash
antma index ./team-memory --db ./team-memory/.antma/index.db
antma doctor ./team-memory --db ./team-memory/.antma/index.db
antma search "launch decision" --db ./team-memory/.antma/index.db
```

## Workspace Shape

```text
team-memory/
  antma.json
  MEMORY.shared.md
  agents/default/MEMORY.md
  ssot/example.md
  daily/example.md
  knowledge-bank/example.md
  curation/promotions/example.md
  evidence/example-packet.md
```

For a richer public-safe example with multiple role memories, source-of-truth
notes, curation, and evidence, see `examples/product-team-memory/`.

## Upgrade Check

After upgrading ANTMA, keep recovery explicit:

```bash
pip install --upgrade antma
antma doctor ./team-memory --db ./team-memory/.antma/index.db
antma init ./team-memory
antma index ./team-memory --db ./team-memory/.antma/index.db
```

`doctor` is read-only. It reports missing or unsupported workspace and index
metadata. `init` adds missing workspace files without overwriting existing files,
and `index` explicitly rebuilds the derived SQLite FTS index.

## Privacy Boundary

This repository is intentionally generic. Do not add private runtime paths,
credentials, customer material, personal chat transcripts, internal project
names, or company-specific operating documents.

See `docs/privacy-boundary.md` for the full rule.

## Community And Contact

ANTMA is maintained as a contributor-led public project. Package authorship is
listed as `ANTMA contributors`, with THEINNOLAB maintaining the public GitHub
repository.

```text
Author: ANTMA contributors
Maintainer: THEINNOLAB
License: Apache License 2.0
Copyright: Copyright 2026 ANTMA contributors
Issues: https://github.com/THEINNOLAB/ANTMA/issues
Security: Prefer GitHub private vulnerability reporting. If unavailable, open a public-safe issue requesting a private disclosure channel; do not include sensitive details in the public issue.
```

## License

ANTMA is licensed under the Apache License 2.0. See `LICENSE`.

## Project Status

ANTMA is an early public beta release candidate. The first goal is to make the
architecture, schemas, resolver, sanitizer, templates, local search path,
promotion flow, and evidence flow clear enough to review and use from source.

The repository includes public-release preparation docs, issue and pull request
templates, and a GitHub Actions test workflow. Package registry publication is a
separate later step after release review is finalized.
