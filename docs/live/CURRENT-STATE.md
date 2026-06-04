# Current State

Updated: 2026-06-04

ANTMA is an early public beta for a local-first, filesystem-first memory
promotion engine.

Public repository URL: `https://github.com/THEINNOLAB/ANTMA`

```text
Author: ANTMA contributors
Maintainer: THEINNOLAB
License: Apache License 2.0
Copyright: Copyright 2026 ANTMA contributors
Issues: https://github.com/THEINNOLAB/ANTMA/issues
Security: Prefer GitHub private vulnerability reporting. If unavailable, open a public-safe issue requesting a private disclosure channel; do not include sensitive details in the public issue.
```

## Ready

- Core package, CLI, schemas, resolver, sanitizer, SQLite FTS index, legacy
  Markdown promotion helper, and evidence packet rendering are present.
- ANTMA 0.2 filesystem state is present under `.antma/`: config, policy,
  queues, audit ledger, promotion ledger, snapshots, locks, and tmp staging.
- JSON candidates, policy gate review, approvals, append-only promotion,
  status, ledger inspection, and rollback are implemented.
- Python API entrypoint `AntmaProject` is exported.
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

Before release or publication, run:

```bash
/private/tmp/antma-venv39/bin/python -m pytest
/private/tmp/antma-venv39/bin/python -m compileall src tests
python3.9 -m pytest
python3.9 -m compileall src tests
python3 -m pytest
python3 -m compileall src tests
antma sanitize .
```

The public repository URL is reflected in package and installation metadata.
GitHub private vulnerability reporting is the preferred sensitive disclosure
route when available.
