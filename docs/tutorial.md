# Tutorial

This tutorial walks through a small ANTMA workspace from setup to search.

## 1. Install ANTMA

From a local checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

For editable development installs and Git URL installs, see `INSTALL.md`.

## 2. Create A Workspace

```bash
antma init ./team-memory
```

This creates a generic memory workspace:

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

## 3. Put Memory In The Right Place

Use `daily/` for raw logs. Raw logs are useful context, but they are not durable
truth.

Use `MEMORY.shared.md` for compact shared facts that many agents need.

Use `agents/<name>/MEMORY.md` for role-scoped memory, such as an agent's stable
responsibilities or preferences.

Use `ssot/` for reviewed source-of-truth notes. These should outrank ordinary
memory and search results.

Use `knowledge-bank/` for reusable research, methods, examples, and reference
material.

## 4. Review Before Promotion

Promotion candidates belong in `curation/promotions/`. A candidate is a review
object, not durable truth. It should explain the source, reason, sensitivity,
and review decision.

Create a candidate from a daily note:

```bash
antma promote ./team-memory/daily/example.md --reason "Reviewed candidate fact."
```

## 5. Record Evidence

Evidence packets belong in `evidence/`. Use them for claims such as "complete",
"ready", or "cleared".

A useful evidence packet includes:

- objective
- completion criteria
- commands or artifacts checked
- pass, partial, failed, or blocked status
- remaining risk
- next action

```bash
antma evidence --objective "Release readiness" --status pass \
  --criterion "tests pass" --evidence "pytest=pass=all tests passed" \
  --output ./team-memory/evidence/release-readiness.md
```

## 6. Scan Before Sharing

Before sharing a workspace or repository:

```bash
antma sanitize ./team-memory
```

The sanitizer checks for common secret and private-context patterns. It is a
guardrail, not a substitute for manual review.

## 7. Index And Search

Build a local SQLite FTS index:

```bash
antma index ./team-memory --db ./team-memory/.antma/index.db
```

Search the index:

```bash
antma search "launch decision" --db ./team-memory/.antma/index.db
```

Search results are derived views. They do not replace the workspace files as the
canonical ledger. ANTMA re-ranks search matches by memory priority so reviewed
source-of-truth notes outrank lower-trust matches.

## 8. Check After Upgrades

After upgrading ANTMA, run a read-only compatibility check:

```bash
pip install --upgrade antma
antma doctor ./team-memory --db ./team-memory/.antma/index.db
```

If `doctor` reports a missing workspace manifest, run:

```bash
antma init ./team-memory
```

If `doctor` reports a missing, unindexed, or incompatible SQLite index, rebuild
the derived cache explicitly:

```bash
antma index ./team-memory --db ./team-memory/.antma/index.db
```
