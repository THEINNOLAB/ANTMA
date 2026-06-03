# PyPI Release Guide

ANTMA 0.1.0 is published on PyPI:

```bash
pip install antma
```

Project page: `https://pypi.org/project/antma/`

Use this guide for future package releases.

## Prerequisites

- Public repository URL selected: `https://github.com/THEINNOLAB/ANTMA`.
- Maintainer listed as THEINNOLAB with authorship as `ANTMA contributors`.
- Security reporting route configured.
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

## Install Verification

```bash
python -m venv /tmp/antma-install-check
/tmp/antma-install-check/bin/python -m pip install antma
/tmp/antma-install-check/bin/antma --help
```
