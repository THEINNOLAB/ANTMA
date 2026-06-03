# Next Steps

Updated: 2026-06-03

## Before Initial Public GitHub Push

- Run the local verification baseline from `docs/live/CURRENT-STATE.md`.
- Review examples, templates, docs, and generated files for private context.
- Initialize a fresh Git repository from this public snapshot only.
- Connect only the intended public GitHub remote:
  `https://github.com/THEINNOLAB/ANTMA.git`.
- Confirm ignored local artifacts are not staged.
- Configure repository description, topics, license display, and issue settings.
- Enable GitHub private vulnerability reporting if that route will be used for
  sensitive security reports.

## Before Any Package Registry Release

- Build and check distributions with `python -m build` and
  `python -m twine check dist/*`.
- Verify install from a clean environment.
- Prepare release notes from `CHANGELOG.md`.
