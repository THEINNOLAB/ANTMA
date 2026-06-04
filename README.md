# ANTMA

AI-Native Team Memory Architecture.

ANTMA is a local-first Python library and CLI for teams that run AI agents and
need a clear, auditable path from raw operating notes to durable team memory.

It is deliberately small. ANTMA is a filesystem-first memory promotion engine:
it helps teams create candidates, run policy gates, route manual approvals,
append durable memory updates, record ledgers, snapshot changes, and roll back
promotions without turning a search backend into the source of truth.

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
- Policy gates decide whether candidates can promote automatically or need
  manual review.
- Promotions append marker blocks and write audit/promotion ledgers.
- Evidence packets make completion claims auditable.
- External backends may support search or analysis, but they do not own truth.

## Scope

ANTMA owns the public-safe core of team memory:

- canonical memory ledger shape
- workspace layout and manifest
- recall priority rules
- privacy scanning guardrails
- promotion candidates for reviewed memory changes
- policy-gated review and manual approvals
- append-only promotion into Markdown destinations
- audit and promotion ledgers
- rollback by promotion id
- evidence packets for auditable completion claims
- local derived search indexes

ANTMA intentionally does not include:

- agent runtime or execution loops
- chat, email, or delivery automation
- scheduler or cron systems
- agent routing, model orchestration, or persona management
- organization-specific operating rules, names, or workflows
- hosted memory services
- automatic dreaming loops

## Install

```bash
pip install antma
```

For virtual environment setup, source checkout, editable developer install, Git
URL install, and first-run checks, see `INSTALL.md`.

## Documentation

- `INSTALL.md`: PyPI, local checkout, editable, and Git URL install paths.
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

Create and promote a local memory candidate:

```bash
cd ./team-memory
mkdir -p notes memory
printf 'Brad prefers short Korean operating replies.\n' > notes/today.md
printf '# Project Memory\n' > memory/project.md

antma candidate create \
  --source notes/today.md \
  --source-type file \
  --destination memory/project.md \
  --summary "Korean operating reply preference" \
  --text "Brad prefers short Korean operating replies." \
  --scope project \
  --risk low \
  --sensitivity internal \
  --evidence notes/today.md

antma review run --all
antma promote run
antma status --json
```

Manual review candidates can be approved, rejected, held, or edited:

```bash
antma approvals list
antma approvals approve <candidate_id>
antma approvals reject <candidate_id> --reason "source insufficient"
antma approvals hold <candidate_id> --reason "needs confirmation"
antma approvals edit <candidate_id> --text "Updated memory text."
```

Rollback is promotion-ledger based:

```bash
antma ledger show --type promotions
antma rollback <promotion_id>
```

The legacy 0.1 Markdown candidate helper is still available:

```bash
antma promote ./daily/example.md --reason "Candidate durable fact."
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
  .antma/
    config.toml
    policies/default.toml
    queue/
    ledger/audit.jsonl
    ledger/promotions.jsonl
    snapshots/
    locks/
    tmp/
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

## Release

Current source version: `v0.2.0`.

- PyPI: `https://pypi.org/project/antma/`
- Install: `pip install antma`
- PyPI and GitHub Release `v0.2.0` should be published from the release commit.

## Project Status

ANTMA is an early public beta package. Version `0.2.0` introduces the
filesystem-first memory promotion engine while preserving the 0.1 scaffold and
legacy Markdown candidate helper.

The current focus is keeping the promotion engine small, reviewable, and
public-safe while improving examples, tests, documentation, and narrowly scoped
CLI/library behavior.
