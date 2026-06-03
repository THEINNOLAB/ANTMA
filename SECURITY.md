# Security Policy

Thank you for helping keep ANTMA safe.

ANTMA is a local-first architecture and toolkit for AI-native team memory.
Because memory systems may involve sensitive operational context, reports about
privacy, data leakage, unsafe defaults, or secret exposure are taken seriously.

## Supported Versions

ANTMA is currently in an early public release stage. Security reports should
target the latest version on the main branch unless a release policy is
published later.

## Reporting a Vulnerability

Please prefer GitHub private vulnerability reporting if it is available for
this repository.

If private vulnerability reporting is not available, open a public-safe issue
requesting a private disclosure channel. Do not include sensitive details,
exploit steps, secrets, private data, or live vulnerability details in a public
issue.

Use wording like:

> I would like to report a potential security issue privately. Please provide a
> private disclosure channel.

## What to Report

Please report issues such as:

- Accidental exposure of secrets or private data
- Unsafe handling of memory files or knowledge-bank content
- Public examples that include sensitive information
- Sanitizer bypasses
- Path traversal or unsafe file access behavior
- Vulnerabilities in CLI behavior
- Documentation that could encourage unsafe disclosure

## What Not to Include Publicly

Please do not post the following in public issues or pull requests:

- API keys, tokens, credentials, or secrets
- Private user or company memory
- Customer data
- Internal operating documents
- Full exploit details before a private channel is established
- Sensitive local paths or environment details

## Maintainer Response

Maintainers will make a best effort to:

- Acknowledge security reports promptly
- Confirm whether the issue affects ANTMA
- Prioritize fixes based on severity and scope
- Avoid exposing sensitive details during triage
- Credit reporters when appropriate and safe

ANTMA is maintained as an open source project, so response times may vary.
Please avoid public disclosure until maintainers have had a reasonable
opportunity to assess and address the issue.

## License

ANTMA is licensed under the Apache License 2.0.
