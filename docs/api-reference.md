# API Reference

ANTMA is a small pre-release package. The API below describes the public surface
currently exposed by the package and CLI.

## CLI

### `antma init PATH`

Create a generic memory workspace at `PATH`.

Options:

- `--overwrite`: rewrite existing template files.

`init` creates `antma.json` with `format: "antma-workspace"`,
`workspace_schema_version: 1`, and `canonical_ledger: "markdown"`. Running
`init` again adds missing files only unless `--overwrite` is set.

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
