# Security Policy

DreamAxis is a self-hosted runtime platform. Security issues should be reported responsibly.

## Supported focus

The highest-priority security areas are:

- auth mode boundaries (`local_open` vs `password`)
- JWT/session handling
- provider secret storage
- CLI runtime scope enforcement
- Browser runtime isolation
- file/path traversal risks
- unsafe command execution
- knowledge file handling and upload parsing

## How to report a vulnerability

Please avoid posting full exploit details in a public issue first.

Preferred order:

1. use GitHub private vulnerability reporting if it is enabled for the repository
2. if private reporting is not available, open a minimal issue without exploit details and ask maintainers for a private contact path

Include:

- affected version or commit
- deployment mode (`local_open` or `password`)
- reproduction steps
- expected impact
- suggested mitigation if you have one

## What to expect

Maintainers should aim to:

- acknowledge receipt
- reproduce the issue
- assess severity and scope
- prepare a fix or mitigation
- coordinate a responsible disclosure path

## Please do not include

- live secrets
- real API keys
- private personal data
- unnecessary exploit payloads against third-party systems

## Secure contribution reminders

If you contribute security-sensitive changes:

- keep `local_open` behavior explicit
- do not expose decrypted provider secrets in API responses or logs
- sanitize external provider errors before returning them to the UI
- document any new risk boundaries in the same PR
