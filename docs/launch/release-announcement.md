# DreamAxis v0.1.0 - Launch Announcement

DreamAxis is now public.

DreamAxis is a **local-first, open-source agent execution platform** for self-hosted AI workflows. It is built for people who want more than a chat box: bring your own model gateway, keep your own keys and data, and actually execute work through reusable runtimes, skills, and knowledge.

## What DreamAxis already includes

- **no-signup by default** with `AUTH_MODE=local_open`
- **OpenAI-compatible provider connections**
- **CLI Runtime**
- **Browser Runtime (Playwright)**
- **builtin skill packs**
- **builtin knowledge packs**
- **runtime/session/execution visibility**

## Why we built it

Most AI tooling pushes users toward a hosted black box. DreamAxis takes the opposite approach:

- local-first instead of cloud-first
- execution-oriented instead of chat-only
- self-hosted keys and data instead of account lock-in
- reusable system assets instead of one-off prompts

## What this first public release is

DreamAxis v0.1.0 is the foundation for:

- local execution
- provider portability
- reusable skill packs
- reusable knowledge packs
- future agent-role orchestration

## What it is not

This release is intentionally **not**:

- a hosted SaaS
- a forced public-signup product
- a full autonomous multi-agent OS
- a broad native SDK matrix across every model vendor

## First-run path

1. copy `.env.example` to `.env`
2. run Docker Compose
3. enter directly in `local_open`
4. add an OpenAI-compatible API key
5. run a CLI skill
6. run a Browser skill
7. sync builtin knowledge packs
8. upload a document
9. open `/chat/local-demo`
10. inspect `/runtime`

## Repo

- GitHub: [DREAMVFIAUNION/dreamaxis](https://github.com/DREAMVFIAUNION/dreamaxis)
- Release: [v0.1.0](https://github.com/DREAMVFIAUNION/dreamaxis/releases/tag/v0.1.0)

If you want a more open, self-hosted execution foundation for AI workflows, DreamAxis is ready for you to try.
