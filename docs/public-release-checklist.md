# Public Release Checklist

Use this checklist before the owner publishes ANTMA from a clean public release
snapshot.

Do not publish a private working or backup repository as a substitute for the
reviewed public snapshot.

## Package

- [ ] `pyproject.toml` metadata is accurate.
- [ ] `README.md` explains the project and quick start.
- [ ] `README.md` defines ANTMA as a small memory architecture core.
- [ ] `INSTALL.md` covers PyPI, local, editable, and Git URL installation.
- [ ] `LICENSE` contains the Apache License 2.0 text.
- [ ] CLI command works after `pip install antma`.
- [ ] Public repository URL is added to install guidance:
      `https://github.com/THEINNOLAB/ANTMA`.
- [ ] Maintainer is listed as THEINNOLAB and authorship remains
      `ANTMA contributors`.
- [ ] General contact points to GitHub Issues.
- [ ] Security reporting says to prefer GitHub private vulnerability reporting,
      with public-safe issue fallback for requesting a private disclosure
      channel.

## Scope Exclusions

- [ ] No agent runtime, execution loop, or model orchestration is included.
- [ ] No scheduler, cron, messaging, chat, email, or delivery automation is
      included.
- [ ] No hosted memory service behavior is described as part of the core.
- [ ] No organization-specific operating system, private rules, or proprietary
      workflow is included.
- [ ] No personas, channel names, scheduler bindings, or runtime configuration
      appear in public-facing examples.

## Tests

- [ ] `python3 -m pytest -q`
- [ ] `PYTHONPATH=src python3 -m compileall -q src tests`
- [ ] `PYTHONPATH=src python3 -m antma.cli sanitize .`
- [ ] clean venv install from PyPI with `pip install antma`
- [ ] `antma init`, `antma sanitize`, `antma promote`, `antma evidence`, `antma index`, `antma doctor`, and `antma search`

## Privacy

- [ ] No private runtime paths.
- [ ] No credentials or token-like examples.
- [ ] No customer, partner, or personal chat data.
- [ ] No internal project names.
- [ ] No generated artifacts containing private context.
- [ ] `git status --short` has no untracked runtime files.
- [ ] `.openclaw/`, `HEARTBEAT.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, and `USER.md` are absent or ignored.
- [ ] Git history reviewed with `git log --all -S` for private names, paths, and runtime terms.
- [ ] Any private working `origin` remains private and is not used as the public
      release repository.
- [ ] Public release remote or repository is created only by the owner from the
      intended publication account or repository.

## Release Notes

- [ ] Describe ANTMA as an architecture layer, not a memory backend.
- [ ] Explain the canonical ledger rule.
- [ ] Explain that adapters are optional derived views.
- [ ] Mention that examples are synthetic.
- [ ] State that policy-gated promotion is local-first and append-only, while
      agent routing, delivery automation, hosted memory services, and automatic
      dreaming loops are out of scope for the public core.
