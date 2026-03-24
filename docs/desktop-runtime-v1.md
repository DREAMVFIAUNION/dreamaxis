# DreamAxis Desktop Runtime v1

## Scope

Desktop Runtime v1 is the first Windows-focused runtime lane for DreamAxis.

It supports **inspect-first desktop actions** and now includes the first approval-gated control path for real desktop operation.

## Current capabilities

- list top-level windows
- inspect the focused window
- list processes
- read system information
- capture the screen
- OCR / extract visible text when Tesseract is available
- return screenshot and desktop artifacts back to chat and runtime
- execute approval-gated desktop actions:
  - focus window
  - launch allowlisted app
  - click
  - type text
  - press hotkeys

## Current safety model

### Auto-allowed

- all inspect-only desktop actions
- screenshot capture
- OCR / extract-text
- window / process / system reads

### Approval-required and now live

- focus window
- launch allowlisted app
- click
- type text
- press hotkeys

These actions are executed only after the chat approval contract is satisfied and the requested action passes the current runtime policy checks.

## Worker shape

The worker lives in:

- `apps/desktop-worker/`

Key files:

- `apps/desktop-worker/app/main.py`
- `apps/desktop-worker/app/services/desktop_executor.py`

## Runtime expectations

Desktop Runtime v1 is designed for:

- local Windows environments
- host-worker deployment
- runtime-backed artifact collection

### Current deployment note

- The Docker `desktop-worker` service is useful for **registration, API wiring, and degraded-path testing**.
- It is **not** the final Windows control path, because Linux containers cannot enumerate native Windows windows or capture the desktop surface.
- For real Windows-first desktop inspection/control, start the host worker directly:

```powershell
.\scripts\start-desktop-worker.ps1 -InstallDeps -RepoRoot "D:\DreamAxis\dreamaxis"
```

- Recommended default public URL for the host worker:
  - `http://host.docker.internal:8300`
- Recommended runtime identity:
  - `runtime-desktop-host-local`
  - `Host Desktop Runtime`

It is not yet intended for:

- cross-platform parity
- silent background autonomy
- destructive desktop actions
- unrestricted system administration

## Notes

- Screenshot capture uses Pillow `ImageGrab`.
- OCR is best-effort and depends on `tesseract` being available on the machine.
- Accessibility-tree support is currently a stub summary and should be upgraded in the next desktop alpha wave.
