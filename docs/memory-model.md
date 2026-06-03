# Memory Model

ANTMA uses explicit memory kinds, statuses, and sensitivity labels.

## Memory Kinds

`daily_raw`

Raw event stream or work journal. Useful for recent recall, but not durable
truth by itself.

`shared_memory`

Compact shared context that multiple agents may use as a bootstrap.

`agent_local`

Memory scoped to one agent, role, or assistant surface.

`source_of_truth`

Reviewed current truth. This outranks general memory and external recall.

`knowledge_bank`

Reusable knowledge such as research notes, examples, frameworks, and reference
material.

`promotion_candidate`

Pending candidate for durable memory or source-of-truth update.

`evidence_packet`

Structured evidence for completion claims, partial results, blocked status, or
quality review.

`external_backend`

Derived memory returned from a search, graph, vector, or hosted backend.

## Statuses

- `raw`: captured but not reviewed
- `candidate`: awaiting review
- `curated`: accepted durable memory
- `superseded`: replaced by newer truth
- `rejected`: reviewed and declined

## Sensitivity

- `public`: safe for public examples
- `internal`: team-private but non-sensitive
- `confidential`: restricted material
- `secret`: credentials or high-risk material; never store in ANTMA examples

