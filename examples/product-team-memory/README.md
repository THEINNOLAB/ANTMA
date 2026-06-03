# Product Team Memory Example

This is a richer synthetic ANTMA workspace for a small product team preparing a
public beta. It shows how durable memory, role-scoped memory, source-of-truth
notes, daily raw notes, reusable knowledge, promotion review, and evidence can
fit together without becoming an agent runtime.

All names, dates, decisions, and notes are generic examples.

## Try It

```bash
PYTHONPATH=../../src python3 -m antma.cli sanitize .
PYTHONPATH=../../src python3 -m antma.cli index . --db /tmp/antma-product-team-memory.db
PYTHONPATH=../../src python3 -m antma.cli doctor . --db /tmp/antma-product-team-memory.db
PYTHONPATH=../../src python3 -m antma.cli search "pricing" --db /tmp/antma-product-team-memory.db
```

## What To Notice

- `ssot/` contains reviewed current truth.
- `MEMORY.shared.md` keeps only compact durable context.
- `agents/*/MEMORY.md` keeps role-specific durable notes.
- `daily/` holds raw notes that should not become truth automatically.
- `curation/promotions/` records a proposed memory update before acceptance.
- `evidence/` records completion checks and remaining risk.

