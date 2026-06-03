# PyPI Release Guide

ANTMA is not ready for PyPI until public repository metadata, maintainer contact
channels, and release review are finalized. Use this guide as the release path
once those details are ready.

## Prerequisites

- Public repository URL selected.
- Maintainer contact or private vulnerability reporting configured.
- `CHANGELOG.md` updated.
- `SECURITY.md` reviewed.
- Public-safe examples and templates reviewed.
- Git history reviewed for private material.

## Local Checks

```bash
python -m pytest -q
python -m compileall -q src tests
antma sanitize .
```

## Build

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

## TestPyPI

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ antma
antma --help
```

## PyPI

```bash
python -m twine upload dist/*
```

After publishing:

- create a GitHub release
- include release notes
- verify install from a clean environment
- run a sample `antma init`, `sanitize`, `index`, and `search` flow

