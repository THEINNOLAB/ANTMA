# Current State

Updated: 2026-06-03

ANTMA is an initial public GitHub release candidate for a local-first memory
architecture library.

## Ready

- Core package, CLI, schemas, resolver, sanitizer, SQLite FTS index, promotion
  candidate rendering, and evidence packet rendering are present.
- Public-safe examples and templates are included.
- GitHub issue, pull request, and test workflow templates are included.
- Local privacy boundary docs are explicit.

## Boundary

- ANTMA is a memory architecture layer, not an agent runtime.
- Search indexes and adapters are derived views, not canonical truth.
- Public examples must remain synthetic and generic.
- Private paths, credentials, customer data, personal transcripts, and
  organization-specific operating documents do not belong in this repository.

## Verification Baseline

Before the first public push, run:

```bash
python3 -m pytest -q
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m antma.cli sanitize .
```

After creating the public GitHub repository, configure repository metadata,
maintainer contact or private vulnerability reporting, and the final public
clone URL in installation guidance.
