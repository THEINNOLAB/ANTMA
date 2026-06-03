# Architecture

ANTMA has five layers.

## 1. Canonical Memory Ledger

The canonical ledger is local Markdown. It is the source that humans can read,
review, edit, commit, archive, or delete.

External search systems are derived indexes. They may improve recall, but they
do not own truth.

## 2. Memory Hierarchy

ANTMA separates memory into explicit kinds:

- daily raw logs
- shared team memory
- agent-local memory
- source-of-truth documents
- knowledge bank notes
- promotion candidates
- evidence packets
- external backend records

Each kind has a different role in recall and review.

## 3. Promotion Bridge

Raw logs do not become durable truth automatically.

Promotions create reviewable candidates with source, reason, confidence, and
status. A candidate is pending until reviewed.

## 4. Recall Resolver

The resolver enforces priority:

```text
source_of_truth
curated_memory
agent_local
recent_daily
knowledge_bank
external_backend
```

The exact ranking can evolve, but the rule should remain stable: canonical and
reviewed material outranks derived or unreviewed context.

## 5. Adapters

Adapters are optional. They can expose other systems as derived indexes or
analysis views.

Adapter implementations must preserve provenance and must not write directly
to the canonical ledger.

