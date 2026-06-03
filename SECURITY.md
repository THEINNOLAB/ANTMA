# Security Policy

ANTMA is designed as a local-first project. It should not receive secrets,
private runtime configuration, customer data, or personal chat transcripts.

## Supported Versions

ANTMA is currently an early pre-release scaffold. Security fixes should target
the current main branch until public versioning begins.

## Reporting A Vulnerability

Do not post secrets or sensitive reproduction data in public issues.

Prefer GitHub private vulnerability reporting. If unavailable, open a
public-safe issue requesting a private disclosure channel; do not include
sensitive details in the public issue.

## Scope

Please report:

- secret or private-context leakage in generated workspaces
- sanitizer bypasses
- unsafe release guidance
- unexpected network or file-system behavior
- dependency or packaging issues that could expose private data

## Privacy Review

Before publishing any release, run:

```bash
antma sanitize .
```

Then manually review:

- examples and templates
- documentation
- generated files
- screenshots or media
- git history
