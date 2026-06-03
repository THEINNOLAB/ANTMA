# Install ANTMA

ANTMA is a Python package. It can be installed from a local checkout, an
editable developer checkout, or a Git repository URL after the public repository
is created.

## Requirements

- Python 3.9 or newer
- pip
- git, if installing from a repository URL

ANTMA has no runtime third-party dependencies in the initial version.

## Option 1: Install From A Local Checkout

```bash
git clone <public-repository-url> antma
cd antma
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Check the CLI:

```bash
antma --help
```

## Option 2: Editable Developer Install

```bash
git clone <public-repository-url> antma
cd antma
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Option 3: Install From A Git URL

After the repository is intentionally published, users can install directly from
the Git URL. Replace `<account>` with the public GitHub account that owns the
repository:

```bash
pip install "git+https://github.com/<account>/antma.git"
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
