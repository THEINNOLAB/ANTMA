# Privacy Boundary

ANTMA is designed to stay publishable. Keep the repository generic.

## Allowed

- generic schemas
- generic examples
- synthetic sample workspaces
- local-first tooling
- optional adapter stubs
- public-safe documentation

## Not Allowed

- credentials, tokens, secrets, or private keys
- customer or partner data
- private chat transcripts
- internal operating documents
- private absolute paths
- company-specific project names
- proprietary business-model methods
- live runtime, gateway, or messaging configuration

## Release Rule

Publish only from an owner-controlled public release snapshot. Do not publish a
private working or backup repository as a substitute for a reviewed public
snapshot.

Before publishing or sharing this repository, run:

```bash
antma sanitize .
```

Then run an additional manual review for:

- names
- paths
- examples
- screenshots
- generated files
- git history

The sanitizer is a guardrail, not a substitute for review.
