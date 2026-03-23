from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import get_settings

settings = get_settings()


@dataclass
class CliSession:
    session_id: str
    workspace_id: str
    session_type: str
    reusable: bool
    cwd: str
    repo_root: str
    shell: str
    env_whitelist: list[str] = field(default_factory=list)
    last_command_at: str | None = None
    status: str = "idle"


SESSIONS: dict[str, CliSession] = {}


def _resolve_path(repo_root: str, candidate: str | None) -> Path:
    root = Path(repo_root).resolve()
    if not candidate:
        return root
    raw = Path(candidate)
    resolved = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if resolved != root and root not in resolved.parents:
        raise HTTPException(status_code=400, detail="Requested path escapes the runtime repo root")
    return resolved


def create_session(
    *,
    session_id: str,
    workspace_id: str,
    session_type: str,
    reusable: bool,
    context_json: dict[str, Any],
) -> CliSession:
    repo_root = str(_resolve_path(context_json.get("repo_root") or str(settings.repo_root_dir), None))
    cwd = str(_resolve_path(repo_root, context_json.get("cwd")))
    session = CliSession(
        session_id=session_id,
        workspace_id=workspace_id,
        session_type=session_type,
        reusable=reusable,
        cwd=cwd,
        repo_root=repo_root,
        shell=str(context_json.get("shell") or settings.WORKER_SHELL),
        env_whitelist=list(context_json.get("env_whitelist") or []),
    )
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> CliSession:
    session = SESSIONS.get(session_id)
    if not session or session.status == "closed":
        raise HTTPException(status_code=404, detail="CLI session not found")
    return session


def close_session(session_id: str) -> None:
    session = get_session(session_id)
    session.status = "closed"


def _command_prefix(shell: str) -> list[str]:
    normalized = shell.lower()
    if normalized in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
        return [shell, "-NoLogo", "-NoProfile", "-Command"]
    return [shell, "-lc"]


def _truncate(value: str) -> str:
    if len(value) <= settings.CLI_MAX_OUTPUT_CHARS:
        return value
    return value[: settings.CLI_MAX_OUTPUT_CHARS]


def execute_command(session_id: str, command: str, cwd: str | None = None) -> dict[str, Any]:
    cli_session = get_session(session_id)
    resolved_cwd = str(_resolve_path(cli_session.repo_root, cwd or cli_session.cwd))
    if not Path(resolved_cwd).exists():
        cli_session.status = "idle"
        raise HTTPException(
            status_code=400,
            detail=(
                "Runtime host cannot access the requested workspace path. "
                "If you are using Docker, mount the workspace into the worker container or use a host runtime."
            ),
        )
    cli_session.status = "busy"
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [*_command_prefix(cli_session.shell), command],
            cwd=resolved_cwd,
            capture_output=True,
            text=True,
            timeout=settings.CLI_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        cli_session.status = "idle"
        raise HTTPException(status_code=408, detail=f"CLI command timed out after {settings.CLI_COMMAND_TIMEOUT_SECONDS}s") from exc

    cli_session.status = "idle"
    cli_session.cwd = resolved_cwd
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "session_id": cli_session.session_id,
        "cwd": resolved_cwd,
        "command": command,
        "stdout": _truncate(completed.stdout or ""),
        "stderr": _truncate(completed.stderr or ""),
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "artifacts_json": [],
    }


def read_file(path: str) -> dict[str, Any]:
    resolved = _resolve_path(str(settings.repo_root_dir), path)
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": str(resolved), "content": _truncate(resolved.read_text(encoding="utf-8", errors="ignore"))}


def list_dir(path: str | None = None) -> dict[str, Any]:
    resolved = _resolve_path(str(settings.repo_root_dir), path)
    if not resolved.exists() or not resolved.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")
    entries = [
        {
            "name": item.name,
            "path": str(item),
            "kind": "dir" if item.is_dir() else "file",
        }
        for item in sorted(resolved.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
    ]
    return {"path": str(resolved), "entries": entries}
