# Next Steps

Updated: 2026-06-04

## Before 0.2 Package Registry Release

- Run the local verification baseline from `docs/live/CURRENT-STATE.md`.
- Review examples, templates, docs, generated files, and changelog entries for
  private context.
- Build and check distributions with `python -m build` and
  `python -m twine check dist/*`.
- Verify install from a clean Python 3.9 environment and current Python.
- Prepare GitHub release notes from `CHANGELOG.md`.
- Publish to PyPI only after the release commit is merged to `main`.

## Product Follow-Ups

- Add richer public-safe examples for manual approvals and rollback.
- Consider `antma doctor` checks for `.antma/` policy, queue, ledger, snapshot,
  and lock integrity.
- Keep SQLite/search as derived views; do not make indexes canonical truth.
