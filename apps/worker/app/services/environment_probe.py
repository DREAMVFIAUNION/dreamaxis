from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_binary(command: list[str], *, tool: str, required: bool, source: str | None = None) -> dict:
    executable = command[0]
    resolved = shutil.which(executable) if Path(executable).name == executable else executable
    if not resolved:
        return {
            "name": tool,
            "installed": False,
            "version": None,
            "required": required,
            "status": "missing" if required else "degraded",
            "source": source or executable,
            "message": f"{tool} is not available in PATH.",
        }

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        output = (completed.stdout or completed.stderr or "").strip().splitlines()
        version = output[0] if output else None
        installed = completed.returncode == 0
        return {
            "name": tool,
            "installed": installed,
            "version": version,
            "required": required,
            "status": "ready" if installed else ("missing" if required else "degraded"),
            "source": source or executable,
            "message": None if installed else f"{tool} probe failed with exit code {completed.returncode}.",
        }
    except Exception as exc:
        return {
            "name": tool,
            "installed": False,
            "version": None,
            "required": required,
            "status": "missing" if required else "degraded",
            "source": source or executable,
            "message": f"{tool} probe failed: {exc}",
        }


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


def _workspace_capability(name: str, installed: bool, message: str) -> dict:
    return {
        "name": name,
        "installed": installed,
        "version": None,
        "required": False,
        "status": "ready" if installed else "degraded",
        "source": "workspace",
        "message": message,
    }


def probe_environment() -> dict:
    repo_root = settings.repo_root_dir
    package_manager = _probe_binary(["pnpm", "--version"], tool="package_manager", required=True, source="pnpm")
    if not package_manager["installed"]:
        package_manager = _probe_binary(["npm", "--version"], tool="package_manager", required=True, source="npm")

    machine_capabilities = [
        _probe_binary(["git", "--version"], tool="git", required=True),
        _probe_binary(["node", "--version"], tool="node", required=True),
        package_manager,
        _probe_binary([sys.executable, "--version"], tool="python", required=True, source=sys.executable),
        _probe_binary(["docker", "--version"], tool="docker", required=False),
        _probe_binary([settings.WORKER_SHELL, "-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], tool="shell_profile", required=False, source=settings.WORKER_SHELL),
    ]

    workspace_capabilities = [
        _workspace_capability("safe_root", repo_root.exists() and repo_root.is_dir(), f"Workspace root: {repo_root}"),
        _workspace_capability("workspace_repo", (repo_root / ".git").exists(), "Detected .git directory." if (repo_root / ".git").exists() else "No .git directory detected."),
        _workspace_capability("node_project", (repo_root / "package.json").exists(), "Detected package.json." if (repo_root / "package.json").exists() else "No package.json detected."),
        _workspace_capability(
            "python_project",
            any((repo_root / name).exists() for name in ("pyproject.toml", "requirements.txt", "setup.py")),
            "Detected Python project files."
            if any((repo_root / name).exists() for name in ("pyproject.toml", "requirements.txt", "setup.py"))
            else "No Python project files detected.",
        ),
        _workspace_capability(
            "docker_project",
            any((repo_root / name).exists() for name in ("Dockerfile", "docker-compose.yml", "compose.yml")) or (repo_root / "infrastructure" / "docker" / "docker-compose.yml").exists(),
            "Detected Docker project files."
            if any((repo_root / name).exists() for name in ("Dockerfile", "docker-compose.yml", "compose.yml")) or (repo_root / "infrastructure" / "docker" / "docker-compose.yml").exists()
            else "No Docker project files detected.",
        ),
    ]

    machine_summary = _summary(machine_capabilities)
    workspace_summary = _summary(workspace_capabilities)
    doctor_status = "missing" if machine_summary["status"] == "missing" else "degraded" if ("degraded" in {machine_summary["status"], workspace_summary["status"]}) else "ready"

    return {
        "profile": "desktop-standard-v1",
        "checked_at": utcnow_iso(),
        "doctor_status": doctor_status,
        "machine": {
            "capabilities": machine_capabilities,
            "summary": machine_summary,
        },
        "workspace": {
            "root_path": str(repo_root),
            "capabilities": workspace_capabilities,
            "summary": workspace_summary,
        },
    }
