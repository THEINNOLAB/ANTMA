# Next Steps

Updated: 2026-06-03

## Before Initial Public GitHub Push

- Run the local verification baseline from `docs/live/CURRENT-STATE.md`.
- Review examples, templates, docs, and generated files for private context.
- Initialize a fresh Git repository from this public snapshot only.
- Connect only the intended public GitHub remote.
- Confirm ignored local artifacts are not staged.

## After Public GitHub Repository Exists

- Replace public clone and Git URL examples with the final repository URL.
- Configure repository description, topics, license display, and issue settings.
- Enable GitHub private vulnerability reporting or publish a maintainer contact
  channel.
- Confirm the GitHub Actions test workflow passes on the public repository.

## Before Any Package Registry Release

- Add final package metadata URLs to `pyproject.toml`.
- Build and check distributions with `python -m build` and
  `python -m twine check dist/*`.
- Verify install from a clean environment.
- Prepare release notes from `CHANGELOG.md`.
