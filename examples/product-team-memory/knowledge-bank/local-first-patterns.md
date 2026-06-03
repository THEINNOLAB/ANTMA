# Local-First Memory Patterns

Status: reusable

## Pattern

Keep the canonical memory ledger in files that humans can inspect, review, and
version. Treat indexes, embeddings, and external stores as derived views.

## Useful When

- Teams need auditability for agent memory.
- Reviewers need to inspect what became durable memory.
- Search should support recall without becoming the source of truth.

## Trade-Off

Local-first systems need explicit sync, backup, and review habits. The benefit
is that ownership and privacy boundaries remain visible.

