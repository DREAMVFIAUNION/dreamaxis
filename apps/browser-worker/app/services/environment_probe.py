from __future__ import annotations

from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary(capabilities: list[dict]) -> dict:
    missing_required = [item["name"] for item in capabilities if item.get("required") and not item.get("installed")]
    warnings = [item["name"] for item in capabilities if not item.get("required") and not item.get("installed")]
    if missing_required:
        status = "missing"
    elif warnings:
        status = "degraded"
    else:
        status = "ready"
    return {
        "status": status,
        "missing_required": missing_required,
        "warnings": warnings,
        "ready_count": sum(1 for item in capabilities if item.get("status") == "ready"),
        "degraded_count": sum(1 for item in capabilities if item.get("status") == "degraded"),
        "missing_count": sum(1 for item in capabilities if item.get("status") == "missing"),
    }


def probe_environment(*, browser_ready: bool) -> dict:
    machine_capabilities = [
        {
            "name": "browser_runtime",
            "installed": browser_ready,
            "version": "chromium",
            "required": False,
            "status": "ready" if browser_ready else "degraded",
            "source": "playwright",
            "message": "Browser worker can launch Chromium." if browser_ready else "Browser worker could not start Chromium.",
        },
        {
            "name": "playwright",
            "installed": browser_ready,
            "version": "chromium",
            "required": False,
            "status": "ready" if browser_ready else "degraded",
            "source": "playwright",
            "message": "Playwright browser binaries are installed." if browser_ready else "Playwright browser binaries are missing or unavailable.",
        },
    ]
    machine_summary = _summary(machine_capabilities)
    return {
        "profile": "desktop-standard-v1",
        "checked_at": utcnow_iso(),
        "doctor_status": machine_summary["status"],
        "machine": {
            "capabilities": machine_capabilities,
            "summary": machine_summary,
        },
        "workspace": {
            "root_path": None,
            "capabilities": [],
            "summary": _summary([]),
        },
    }
