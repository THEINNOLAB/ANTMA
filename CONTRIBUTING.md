# Contributing

ANTMA is an early local-first memory architecture library. Contributions should
keep the project generic, privacy-safe, and easy to review.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite before opening a pull request:

```bash
python -m pytest -q
python -m compileall -q src tests
antma sanitize .
```

## Contribution Guidelines

- Keep examples synthetic and public-safe.
- Do not add credentials, private paths, personal chat transcripts, customer
  data, or company-specific operating documents.
- Prefer small, focused changes with clear tests or documentation.
- Update docs when behavior, CLI commands, schemas, or workspace shape changes.
- Add an evidence note when a change claims release readiness or completion.

## Documentation Rules

- Current project state belongs in `docs/live/CURRENT-STATE.md`.
- Next actions belong in `docs/live/NEXT-STEPS.md`.
- Work events belong in `docs/live/WORKLOG.md`.
- Stable explanations belong in top-level files under `docs/`.

## Pull Request Checklist

- [ ] The change is generic and privacy-safe.
- [ ] Tests pass locally.
- [ ] `antma sanitize .` reports no findings.
- [ ] Relevant docs are updated.
- [ ] Remaining risks or follow-up work are stated.

