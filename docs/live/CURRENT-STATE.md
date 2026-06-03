# Current State

Updated: 2026-06-03

ANTMA is an initial public GitHub release candidate for a local-first memory
architecture library.

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

The public repository URL is reflected in package and installation metadata.
Before pushing, configure repository metadata and enable GitHub private
vulnerability reporting if that route will be used for sensitive reports.
