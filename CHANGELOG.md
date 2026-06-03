# Changelog

All notable changes to ANTMA will be documented in this file.

This project follows semantic versioning once package registry releases begin.
Before then, entries may describe public release-candidate milestones.

## Unreleased

- Clarified public beta scope: ANTMA remains a small memory architecture core,
  not an agent runtime, scheduler, messaging system, routing layer, hosted
  memory service, or organization-specific operating system.
- Added a richer synthetic product-team memory example with shared memory,
  role memory, source-of-truth notes, daily raw notes, knowledge bank content,
  promotion review, and evidence.
- Added a workspace manifest, index compatibility metadata, `antma doctor`, and
  read-only search failure behavior for missing or incompatible derived indexes.
- Hardened the early beta path with Python 3.9-compatible annotations,
  runtime artifact leak detection, resolver-ranked search, and CLI commands for
  promotion candidates and evidence packets.
- Added contributor, security, release, tutorial, API, and GitHub template
  documentation for public-release preparation.
- Added GitHub Actions test workflow for package install, tests, compile checks,
  and privacy scanning.

## 0.1.0 - Initial Scaffold

- Created the initial local-first memory architecture package.
- Added workspace scaffolding, memory schemas, recall resolver, SQLite FTS
  indexing, promotion helpers, evidence packet rendering, and privacy scanning.
- Added CLI commands: `init`, `sanitize`, `index`, and `search`.
- Added install documentation and a public-release checklist.
