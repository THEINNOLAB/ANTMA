# API Reference

ANTMA is a small public beta package. The API below describes the public surface
currently exposed by the package and CLI, including the 0.2 filesystem-first
promotion engine.

## CLI

### `antma init [PATH]`

Create a generic memory workspace at `PATH`.

Options:

- `--force`: supplement missing `.antma/` state without deleting queues,
  ledgers, snapshots, locks, or tmp files.
- `--overwrite`: rewrite existing scaffold template files.
- `--overwrite config --overwrite policy`: rewrite targeted `.antma` defaults.

`init` creates the 0.1 scaffold and the 0.2 `.antma/` local state layout.
Running `init` again adds missing files only unless overwrite options are set.

### `antma candidate create|list|show|delete`

Create and inspect JSON memory candidates in `.antma/queue/`.

`candidate create` accepts:

- `--source`
- `--source-type file|manual|message|api`
- `--destination`
- `--summary`
- `--text`
- `--scope personal|project|shared|persona|ssot|security`
- `--risk low|medium|high|critical`
- `--sensitivity public|internal|sensitive|secret`
- `--supersedes`, repeatable
- `--evidence`, repeatable

Manual source candidates may omit `--source` but still require text, summary,
destination, scope, risk, sensitivity, and evidence completeness.

### `antma review run [CANDIDATE_ID]`

Evaluate candidates against the configured TOML policy.

Options:

- `--all`: include pending candidates, retryable blocked candidates, and
  manual-review or held candidates that need re-evaluation.
- `--policy NAME`: use `.antma/policies/<NAME>.toml`.
- `--json`: output candidate-level gate results.

### `antma approvals list|show|approve|reject|hold|edit`

Manage manual review candidates. Material edits reset gate decisions and move
the candidate back to `candidate` status for review.

### `antma promote run [CANDIDATE_ID]`

Append approved or auto-passed candidates into their Markdown destination using
ANTMA marker blocks.

Options:

- `--dry-run`
- `--fail-fast`
- `--json`

The 0.1 helper `antma promote SOURCE --reason TEXT` remains available and is
separate from `antma promote run`.

### `antma rollback PROMOTION_ID`

Rollback a promotion marker block using `.antma/ledger/promotions.jsonl`.

Options:

- `--dry-run`
- `--json`

Rollback fails with `write_conflict` if the destination no longer matches the
post-promotion hash recorded in the promotion ledger.

### `antma status`

Show queue counts and ledger counts. Use `--json` for machine-readable output.

### `antma ledger show`

Show audit or promotion ledger records.

Options:

- `--type audit|promotions`
- `--candidate CANDIDATE_ID`

### `antma policy validate|show`

Validate or print the configured TOML policy.

### `antma sanitize PATH`

Scan files under `PATH` for common secret and private-context patterns.

Exit codes:

- `0`: no findings
- `1`: one or more findings

### `antma index PATH --db DB`

Index Markdown files under `PATH` into a SQLite FTS database.

The SQLite index is a derived cache. `index` writes compatibility metadata to
`antma_meta`: `index_schema_version`, `workspace_schema_version`, and
`indexed_at`.

### `antma doctor PATH --db DB`

Check workspace and index compatibility without making changes.

Exit codes:

- `0`: workspace manifest and index metadata are compatible
- `1`: one or more compatibility issues were found
- `2`: invalid usage, such as a missing workspace path

### `antma search QUERY --db DB --limit N`

Search a SQLite FTS database created by `antma index`. Results are re-ranked by
ANTMA recall priority, so source-of-truth records outrank lower-trust matches.
`search` is read-only: it does not create a missing DB and asks the user to run
`antma index PATH --db DB` when the index is missing or incompatible.

### `antma promote SOURCE --reason TEXT --output PATH --overwrite`

Create a Markdown promotion candidate from `SOURCE`.

Options:

- `--reason`: required review reason.
- `--output`: optional output path; defaults to `curation/promotions/<source-stem>-promotion.md`.
- `--overwrite`: rewrite an existing candidate file.

### `antma evidence --objective TEXT --status STATUS --criterion TEXT --evidence ITEM --output PATH`

Create a Markdown evidence packet.

Options:

- `--status`: one of `pass`, `partial`, `failed`, or `blocked`.
- `--criterion`: repeatable completion criterion.
- `--evidence`: repeatable `LABEL=RESULT=DETAIL` item.
- `--remaining-risk`: optional remaining risk text.
- `--next-action`: optional next action text.
- `--output`: required output path.
- `--overwrite`: rewrite an existing evidence packet.

## Schemas

Import core schema types from `antma` or `antma.schema`.

```python
from antma import MemoryKind, MemoryRecord, MemoryStatus, Sensitivity
```

### `MemoryKind`

Classifies memory records:

- `DAILY_RAW`
- `SHARED_MEMORY`
- `AGENT_LOCAL`
- `SOURCE_OF_TRUTH`
- `KNOWLEDGE_BANK`
- `PROMOTION_CANDIDATE`
- `EVIDENCE_PACKET`
- `EXTERNAL_BACKEND`

### `MemoryStatus`

Tracks review state:

- `RAW`
- `CANDIDATE`
- `CURATED`
- `SUPERSEDED`
- `REJECTED`

### `Sensitivity`

Tracks expected handling:

- `PUBLIC`
- `INTERNAL`
- `CONFIDENTIAL`
- `SECRET`

### `MemoryRecord`

Dataclass for a memory unit with provenance.

Key methods:

- `as_search_text()`: combine searchable fields.
- `to_dict()`: serialize to a plain dictionary.
- `from_markdown(path, body, kind)`: create a record from Markdown content.

### `EvidencePacket`

Dataclass for auditable completion claims.

## Project API

```python
from antma import AntmaProject

project = AntmaProject.open(".")
candidate = project.create_candidate(
    source="notes/today.md",
    destination="memory/project.md",
    summary="Korean operating reply preference",
    text="Brad prefers short Korean operating replies.",
    scope="project",
    risk="low",
    sensitivity="internal",
)
review_result = project.review.run(candidate_id=candidate.candidate_id)
promotion = project.promote(candidate.candidate_id)
status = project.status()
```

Manual approval API:

```python
project.approvals.list()
project.approvals.show(candidate.candidate_id)
project.approvals.approve(candidate.candidate_id, reviewer="local-user")
project.approvals.reject(candidate.candidate_id, reason="source insufficient")
project.approvals.hold(candidate.candidate_id, reason="needs confirmation")
project.approvals.edit(candidate.candidate_id, proposed_text="Updated text.")
```

Rollback API:

```python
project.rollback("prom_20260604_072500_abcd")
```

## Resolver

```python
from antma.resolver import resolve
```

`resolve(records, query="", limit=10)` returns memory records in recall priority
order. It scores source-of-truth records above general memory, demotes rejected
or high-sensitivity records, and adds a simple query term match score.

## Indexing

```python
from pathlib import Path
from antma.indexer import MemoryIndex

index = MemoryIndex(Path(".antma/index.db"))
index.index_markdown_tree(Path("team-memory"))
results = index.search("launch decision")
```

`MemoryIndex` stores Markdown content in SQLite FTS5. The index is a derived
view; workspace Markdown remains the canonical ledger.

## Scaffolding

```python
from pathlib import Path
from antma.scaffold import create_workspace

written = create_workspace(Path("team-memory"))
```

`create_workspace(root, overwrite=False)` writes the default workspace template
files and returns the paths written.

## Sanitizing

```python
from pathlib import Path
from antma.sanitize import scan_path, format_findings

findings = scan_path(Path("."))
print(format_findings(findings))
```

The sanitizer is intentionally conservative. It is a guardrail for public
release review, not a complete security scanner.

## Evidence Rendering

```python
from antma.evidence import render_evidence_packet
```

`render_evidence_packet(packet)` turns an `EvidencePacket` into Markdown.

## Promotion Rendering

```python
from antma.promotion import render_promotion_candidate
```

`render_promotion_candidate(record, reason)` turns a `MemoryRecord` into a
Markdown review candidate.
