from __future__ import annotations

from typing import Sequence

from app.schemas.desktop_grounding import DesktopContextSnapshot, DesktopTargetResolverResult

APP_ALIAS_MAP: dict[str, dict[str, str | None]] = {
    "vs code": {"app": "Visual Studio Code", "window": "Visual Studio Code", "surface": "editor"},
    "visual studio code": {"app": "Visual Studio Code", "window": "Visual Studio Code", "surface": "editor"},
    "vscode": {"app": "Visual Studio Code", "window": "Visual Studio Code", "surface": "editor"},
    "terminal": {"app": "Terminal", "window": "Terminal", "surface": "shell"},
    "windows terminal": {"app": "Terminal", "window": "Windows Terminal", "surface": "shell"},
    "powershell": {"app": "Terminal", "window": "PowerShell", "surface": "shell"},
    "cmd": {"app": "Terminal", "window": "Command Prompt", "surface": "shell"},
    "browser": {"app": "Browser", "window": "Browser", "surface": "page"},
    "chrome": {"app": "Browser", "window": "Google Chrome", "surface": "page"},
    "edge": {"app": "Browser", "window": "Microsoft Edge", "surface": "page"},
}


def _match_prompt_target(prompt: str) -> dict[str, str | None]:
    lowered = prompt.lower()
    for token, target in APP_ALIAS_MAP.items():
        if token in lowered:
            return dict(target)
    return {"app": None, "window": None, "surface": "desktop"}


def build_desktop_context_snapshot(
    *,
    prompt: str,
    workspace_root: str,
    desktop_runtime_names: Sequence[str],
) -> DesktopContextSnapshot:
    target = _match_prompt_target(prompt)
    prompt_target = target.get("window") or target.get("app") or "Desktop"
    runtime_value = ", ".join(desktop_runtime_names) if desktop_runtime_names else "offline"
    return DesktopContextSnapshot(
        system_info={
            "workspace_root": workspace_root,
            "desktop_runtime": runtime_value,
        },
        process_list=[target["app"]] if target.get("app") else [],
        top_level_windows=[target["window"]] if target.get("window") else [],
        foreground_window=target.get("window"),
        screenshot_summary="No live desktop screenshot was captured before execution." if desktop_runtime_names else "Desktop runtime is offline; no screenshot available yet.",
        ocr_text=prompt_target if target.get("surface") == "page" else None,
        ui_node_summary=f"Prompt-derived desktop surface: {target.get('surface') or 'desktop'}",
        prompt_derived_target=prompt_target,
    )


def resolve_desktop_target(
    *,
    prompt: str,
    workspace_root: str,
    desktop_runtime_names: Sequence[str],
) -> DesktopTargetResolverResult:
    target = _match_prompt_target(prompt)
    context = build_desktop_context_snapshot(
        prompt=prompt,
        workspace_root=workspace_root,
        desktop_runtime_names=desktop_runtime_names,
    )
    if target.get("window"):
        return DesktopTargetResolverResult(
            resolved=True,
            target_type="window",
            target_identifier=str(target["window"]),
            confidence=0.96,
            resolver_path=["explicit_app_window_match"],
            context_snapshot=context,
        )
    if target.get("app"):
        return DesktopTargetResolverResult(
            resolved=True,
            target_type="app",
            target_identifier=str(target["app"]),
            confidence=0.9,
            resolver_path=["explicit_app_window_match"],
            context_snapshot=context,
        )
    if context.ocr_text:
        return DesktopTargetResolverResult(
            resolved=True,
            target_type="ocr_match",
            target_identifier=context.ocr_text,
            confidence=0.72,
            resolver_path=["ocr_text_match"],
            context_snapshot=context,
        )
    return DesktopTargetResolverResult(
        resolved=False,
        target_type="desktop",
        target_identifier=context.prompt_derived_target,
        confidence=0.42,
        resolver_path=["focused_window_fallback"],
        failure_reason="DreamAxis could not match the prompt to a concrete app or window and stayed scoped to the desktop surface.",
        context_snapshot=context,
    )


def build_grounding_signals(result: DesktopTargetResolverResult) -> list[dict[str, str]]:
    context = result.context_snapshot
    signals = [
        {
            "id": "desktop-workspace-root",
            "kind": "workspace_root",
            "label": "Workspace root",
            "value": context.system_info.get("workspace_root", "."),
            "source_layer": "workspace",
            "status": "ready",
            "reason": "Desktop operator turns remain scoped to the active workspace and registered runtimes.",
        },
        {
            "id": "desktop-target",
            "kind": "desktop_target",
            "label": "Prompt target",
            "value": context.prompt_derived_target,
            "source_layer": "request",
            "status": "observed" if result.resolved else "warning",
            "reason": "DreamAxis extracted the likely desktop surface from the user prompt.",
        },
    ]
    runtime_value = context.system_info.get("desktop_runtime", "offline")
    signals.append(
        {
            "id": "desktop-runtime-online" if runtime_value != "offline" else "desktop-runtime-missing",
            "kind": "runtime_inventory",
            "label": "Desktop runtime",
            "value": runtime_value,
            "source_layer": "runtime",
            "status": "ready" if runtime_value != "offline" else "warning",
            "reason": "A Windows desktop runtime is online for this workspace." if runtime_value != "offline" else "No desktop runtime is online, so DreamAxis can only prepare a grounded operator plan.",
        }
    )
    if context.foreground_window:
        signals.append(
            {
                "id": "desktop-foreground-window",
                "kind": "foreground_window",
                "label": "Foreground window",
                "value": context.foreground_window,
                "source_layer": "desktop",
                "status": "observed",
                "reason": "Prompt-derived foreground window candidate for the current desktop turn.",
            }
        )
    return signals


def grounded_target_from_result(result: DesktopTargetResolverResult) -> dict[str, object]:
    target_type = result.target_type if result.resolved else "desktop"
    source_ids = ["desktop-target", "desktop-runtime-online" if result.context_snapshot.system_info.get("desktop_runtime") != "offline" else "desktop-runtime-missing"]
    return {
        "type": target_type,
        "label": result.context_snapshot.ui_node_summary or target_type,
        "value": result.target_identifier or result.context_snapshot.prompt_derived_target,
        "reason": result.failure_reason or f"Resolver path: {' -> '.join(result.resolver_path)}",
        "source_signal_ids": source_ids,
        "status": "primary" if result.resolved else "candidate",
    }
