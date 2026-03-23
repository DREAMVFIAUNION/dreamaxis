from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException


CLI_DENYLIST = [
    "remove-item",
    "del ",
    "del\t",
    "format ",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "set-executionpolicy",
    "reg delete",
    "rmdir ",
]

BROWSER_ALLOWED_ACTIONS = {
    "open_url",
    "click",
    "hover",
    "type",
    "select_option",
    "press",
    "wait_for",
    "extract_text",
    "extract_links",
    "take_screenshot",
    "list_tabs",
    "close_tab",
}


def validate_cli_command(command: str) -> str:
    normalized = " ".join(command.strip().split())
    lowered = normalized.lower()
    for token in CLI_DENYLIST:
        if token in lowered:
            raise HTTPException(status_code=400, detail=f"Command is blocked by runtime policy: {token}")
    return normalized


def resolve_workspace_path(workspace_root: str, working_directory: str | None) -> Path:
    root = Path(workspace_root).resolve()
    candidate = root if not working_directory else Path(working_directory)
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if resolved != root and root not in resolved.parents:
        raise HTTPException(status_code=400, detail="Working directory must stay inside the workspace root")
    return resolved


def ensure_runtime_type(required_runtime_type: str | None, expected: str = "cli") -> None:
    if required_runtime_type and required_runtime_type != expected:
        raise HTTPException(status_code=400, detail=f"Skill requires runtime '{required_runtime_type}', not '{expected}'")


def validate_browser_actions(actions: list[dict]) -> list[dict]:
    if not actions:
        raise HTTPException(status_code=400, detail="Browser skill requires at least one action")
    normalized: list[dict] = []
    for action in actions:
        action_name = str(action.get("action") or "").strip()
        if not action_name or action_name not in BROWSER_ALLOWED_ACTIONS:
            raise HTTPException(status_code=400, detail=f"Browser action is not allowed: {action_name or 'unknown'}")
        normalized.append({**action, "action": action_name})
    return normalized
