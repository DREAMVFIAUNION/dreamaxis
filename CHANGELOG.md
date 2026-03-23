# Changelog

All notable changes to DreamAxis will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- GitHub community scaffolding:
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
  - `SUPPORT.md`
- GitHub issue and pull request templates
- GitHub Actions CI workflow for:
  - Python compile checks
  - web build
  - Docker smoke validation
- local demo reset scripts:
  - `scripts/reset-local-demo.py`
  - `scripts/reset-local-demo.ps1`
- release support docs:
  - `docs/release-checklist.md`
  - `docs/github-release-template.md`
  - `docs/screenshots.md`

### Changed

- README upgraded for public GitHub release readiness
- architecture doc refreshed with a mermaid system overview

## [0.1.0] - 2026-03-23

### Added

- local-first DreamAxis monorepo foundation
- Next.js web control center
- FastAPI backend API
- PostgreSQL + Redis + Docker Compose local stack
- `local_open` auth mode with bootstrap session flow
- optional `password` auth mode
- OpenAI-compatible provider connection management
- dynamic model selection flow
- knowledge uploads and builtin knowledge packs
- skill packs with prompt / CLI / browser modes
- CLI Runtime v1
- Browser Runtime v1 (Playwright)
- runtime/session/execution visibility in the UI
- agent role registry foundation
