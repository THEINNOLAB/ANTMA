# Install ANTMA

ANTMA is a Python package. It can be installed from a local checkout, an
editable developer checkout, PyPI, or the public Git repository.

## Requirements

- Python 3.9 or newer
- pip
- git, if installing from a repository URL

ANTMA has no runtime third-party dependencies in the initial version.

## Option 1: Install From PyPI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install antma
```

Check the CLI:

```bash
antma --help
```

## Option 2: Install From A Local Checkout

```bash
git clone https://github.com/THEINNOLAB/ANTMA.git antma
cd antma
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Check the CLI:

```bash
antma --help
```

## Option 3: Editable Developer Install

```bash
git clone https://github.com/THEINNOLAB/ANTMA.git antma
cd antma
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Option 4: Install From A Git URL

Users can install directly from the Git URL:

```bash
pip install "git+https://github.com/THEINNOLAB/ANTMA.git"
```

## First Workspace

Create and inspect a sample local memory workspace:

```bash
antma init ./team-memory
antma sanitize ./team-memory
antma index ./team-memory --db ./team-memory/.antma/index.db
antma search "truth" --db ./team-memory/.antma/index.db
```

## Privacy Check Before Sharing

Before publishing a workspace or repository copy, run:

```bash
antma sanitize .
```

Then do a manual review of examples, generated files, screenshots, and git
history.
