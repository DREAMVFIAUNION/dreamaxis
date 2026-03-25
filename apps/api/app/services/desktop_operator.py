from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.runtime_execution import RuntimeExecution
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.message import ChatMode, KnowledgeChunkReference
from app.services.execution_annotations import build_annotation
from app.services.desktop_grounding import build_grounding_signals, grounded_target_from_result, resolve_desktop_target
from app.services.runtime_dispatcher import dispatch_desktop_execution
from app.services.runtime_registry import list_runtimes_for_workspace
from app.services.runtime_service import (
    create_runtime_execution,
    mark_runtime_failed,
    mark_runtime_running,
    mark_runtime_succeeded,
    publish_runtime_state,
)

DESKTOP_MODE_LABELS: dict[ChatMode, str] = {
    "inspect_desktop": "Inspect desktop",
    "verify_desktop": "Verify desktop",
    "operate_desktop": "Operate desktop",
    "understand_repo": "Understand repo",
    "inspect_repo": "Inspect repo",
    "verify_repo": "Verify repo",
    "propose_fix": "Propose fix",
}

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
HOTKEY_PATTERN = re.compile(r"(ctrl|control|alt|shift|win|windows)\s*(?:\+\s*|\-\s*)([a-z0-9]+(?:\s*(?:\+\s*|\-\s*)(?:[a-z0-9]+))*)", re.IGNORECASE)
SIMPLE_PRESS_PATTERN = re.compile(r"\bpress\s+(enter|tab|esc|escape|space|up|down|left|right|home|end|pageup|pagedown|f(?:1[0-2]|[1-9]))\b", re.IGNORECASE)
CLICK_PATTERN = re.compile(r"\bclick(?:\s+at)?\s*\(?\s*(\d{1,5})\s*[, ]\s*(\d{1,5})\s*\)?", re.IGNORECASE)
QUOTED_TEXT_PATTERN = re.compile(r"[\"'](.+?)[\"']")


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in (value or []) if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _safe_artifacts(value: Any) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _build_trace_runtime_details(existing: dict[str, Any] | None, trace: dict[str, Any]) -> dict[str, Any]:
    payload = dict(existing or {})
    payload["mode"] = trace.get("mode")
    payload["execution_bundle_id"] = trace.get("execution_bundle_id")
    payload["child_execution_ids"] = trace.get("child_execution_ids") or []
    payload["proposal"] = trace.get("proposal")
    payload["workspace_readiness"] = trace.get("workspace_readiness")
    payload["execution_trace"] = trace
    payload["evidence_items"] = trace.get("evidence_items") or trace.get("evidence") or []
    payload["recommended_next_actions"] = trace.get("recommended_next_actions") or []
    payload["trace_summary"] = trace.get("trace_summary")
    return payload


async def _persist_parent_trace(
    session: AsyncSession,
    *,
    execution: RuntimeExecution,
    trace: dict[str, Any],
) -> RuntimeExecution:
    execution.details_json = _build_trace_runtime_details(execution.details_json, trace)
    if trace.get("artifact_summaries") is not None:
        execution.artifacts_json = trace.get("artifact_summaries")
    await session.commit()
    await session.refresh(execution)
    await publish_runtime_state(execution)
    return execution


def _normalize_operate_actions(requested_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for action in requested_actions:
        normalized.append(
            {
                "action": action.get("action"),
                "arguments": action.get("arguments") if isinstance(action.get("arguments"), dict) else {},
                "target_app": action.get("target_app"),
                "target_window": action.get("target_window"),
                "target_label": action.get("target_label"),
                "title": action.get("title"),
                "id": action.get("id"),
            }
        )
    return normalized


def _summarize_desktop_action_result(result: dict[str, Any], *, requested_actions: list[dict[str, Any]]) -> tuple[str, list[str]]:
    action_results = _dict_list(result.get("action_results"))
    warnings = _string_list(result.get("warnings"))
    action_names = [str(item.get("action") or "").strip() for item in action_results if str(item.get("action") or "").strip()]
    if action_names:
        if len(action_names) == 1:
            summary = f"Executed approved desktop action `{action_names[0]}`."
        else:
            summary = "Executed approved desktop action sequence: " + " -> ".join(f"`{name}`" for name in action_names) + "."
    elif requested_actions:
        fallback_names = [str(item.get("action") or "desktop") for item in requested_actions]
        if len(fallback_names) == 1:
            summary = f"Executed approved desktop action `{fallback_names[0]}`."
        else:
            summary = "Executed approved desktop action sequence: " + " -> ".join(f"`{name}`" for name in fallback_names) + "."
    else:
        summary = "Executed approved desktop action."
    if warnings:
        summary = f"{summary} {warnings[0]}"
    return summary, warnings


def _build_action_result_step(
    *,
    child_execution: RuntimeExecution,
    requested_actions: list[dict[str, Any]],
    result: dict[str, Any],
    status: str,
    summary: str,
    warnings: list[str],
) -> dict[str, Any]:
    action_results = _dict_list(result.get("action_results"))
    first_result = action_results[0] if action_results else {}
    label = None
    if isinstance(result.get("active_window"), dict):
        label = result["active_window"].get("title")
    if not label and isinstance(result.get("focused_window"), dict):
        label = result["focused_window"].get("title")
    if not label:
        label = requested_actions[0].get("target_window") or requested_actions[0].get("target_app") or requested_actions[0].get("target_label")
    output_excerpt = str(first_result or result.get("active_window") or result.get("focused_window") or summary)
    if warnings:
        output_excerpt = f"{output_excerpt}\n\nWarnings:\n- " + "\n- ".join(warnings[:3])
    return {
        "kind": "desktop",
        "title": "Approved desktop action",
        "summary": summary,
        "status": status,
        "runtime_execution_id": child_execution.id,
        "runtime_session_id": result.get("runtime_session_id"),
        "command_preview": _normalize_operate_actions(requested_actions),
        "output_excerpt": output_excerpt,
        "artifact_summaries": _safe_artifacts(result.get("artifacts_json")),
        "label": label,
        "current_url": None,
        "is_read_only": False,
        "warnings": warnings,
    }


def _build_action_result_evidence(
    *,
    child_execution: RuntimeExecution,
    requested_actions: list[dict[str, Any]],
    result: dict[str, Any],
    summary: str,
    warnings: list[str],
) -> dict[str, Any]:
    label = requested_actions[0].get("target_window") or requested_actions[0].get("target_app") or requested_actions[0].get("target_label")
    return {
        "title": "Approved desktop action",
        "type": "desktop_capture",
        "runtime_execution_id": child_execution.id,
        "content": summary,
        "label": label,
        "command_preview": str(_normalize_operate_actions(requested_actions)),
        "stderr_excerpt": "\n".join(warnings[:3]) if warnings else None,
        "artifact_summaries": _safe_artifacts(result.get("artifacts_json")),
        "metadata": {
            "requested_actions": requested_actions,
            "action_results": _dict_list(result.get("action_results")),
            "active_window": result.get("active_window"),
            "focused_window": result.get("focused_window"),
            "warnings": warnings,
            "environment": result.get("environment"),
        },
    }


def infer_desktop_mode(prompt: str, requested_mode: ChatMode | None) -> tuple[str, str, ChatMode]:
    if requested_mode in {"inspect_desktop", "verify_desktop", "operate_desktop"}:
        label = {
            "inspect_desktop": "desktop inspection",
            "verify_desktop": "desktop verification",
            "operate_desktop": "desktop operation planning",
        }[requested_mode]
        return (
            "desktop_operator",
            f"Using explicit desktop mode for {label}.",
            requested_mode,
        )

    lowered = prompt.lower()
    if any(token in lowered for token in ["open", "click", "type", "switch window", "focus", "launch", "press"]):
        return "desktop_operator", "The prompt requests a state-changing desktop action, so route it through the desktop operator lane.", "operate_desktop"
    if any(token in lowered for token in ["screenshot", "screen", "ocr", "visible", "verify desktop", "active window"]):
        return "desktop_operator", "The prompt asks for current desktop state verification with visible evidence.", "verify_desktop"
    return "desktop_operator", "Defaulting to desktop inspection for desktop/operator-style prompts.", "inspect_desktop"


def detect_desktop_target(prompt: str) -> dict[str, str | None]:
    lowered = prompt.lower()
    for token, target in APP_ALIAS_MAP.items():
        if token in lowered:
            return dict(target)
    return {"app": None, "window": None, "surface": "desktop"}


def _slug(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "desktop-action").strip().lower()).strip("-") or "desktop-action"


def _extract_hotkey(prompt: str) -> str | None:
    lowered = prompt.lower()
    match = HOTKEY_PATTERN.search(lowered)
    if match:
        tokens = re.split(r"\s*(?:\+|\-)\s*", match.group(0).replace("press", "").strip())
        normalized = [token for token in (item.strip() for item in tokens) if token]
        if normalized:
            return "+".join(normalized)
    match = SIMPLE_PRESS_PATTERN.search(lowered)
    if match:
        return match.group(1).lower()
    return None


def _extract_type_text(prompt: str) -> str | None:
    lowered = prompt.lower()
    if not any(token in lowered for token in ["type ", "enter text", "input "]):
        return None
    quoted = QUOTED_TEXT_PATTERN.search(prompt)
    if quoted:
        return quoted.group(1).strip()
    type_match = re.search(r"\b(?:type|enter text|input)\s+(.+)", prompt, re.IGNORECASE)
    if not type_match:
        return None
    candidate = type_match.group(1).strip().rstrip(".")
    candidate = re.split(r"\b(?:into|in|on)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return candidate or None


def _extract_click_coordinates(prompt: str) -> tuple[int, int] | None:
    match = CLICK_PATTERN.search(prompt)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _build_requested_actions(prompt: str, target: dict[str, str | None]) -> list[dict[str, Any]]:
    lowered = prompt.lower()
    target_value = target.get("window") or target.get("app") or "Desktop"
    target_app = target.get("app")
    target_window = target.get("window")
    focus_arguments = {"target": target_window or target_value}
    actions: list[dict[str, Any]] = []

    def add_action(
        action: str,
        title: str,
        *,
        arguments: dict[str, Any] | None = None,
        risk_note: str | None = None,
        target_label: str | None = None,
    ) -> None:
        actions.append(
            {
                "id": f"{_slug(action)}-{len(actions) + 1}",
                "action": action,
                "title": title,
                "target_label": target_label or target_value,
                "target_app": target_app,
                "target_window": target_window,
                "risk_note": risk_note or "This action changes desktop state and must be explicitly approved before execution.",
                "arguments": arguments or {},
                "requires_confirmation": True,
            }
        )

    click_coords = _extract_click_coordinates(prompt)
    hotkey = _extract_hotkey(prompt)
    type_text = _extract_type_text(prompt)

    if any(token in lowered for token in ["open ", "launch ", "start "]) and target_app:
        launch_args: dict[str, Any] = {"target_app": target_app}
        url_match = re.search(r"(https?://\S+)", prompt, re.IGNORECASE)
        if url_match:
            launch_args["url"] = url_match.group(1)
        add_action("launch_app", f"Launch {target_app}", arguments=launch_args)
        return actions

    if click_coords:
        if target_window or target_app:
            add_action("focus_window", f"Focus {target_value}", arguments=focus_arguments)
        add_action(
            "click",
            f"Click {click_coords[0]},{click_coords[1]}",
            arguments={"x": click_coords[0], "y": click_coords[1], "button": "left", "clicks": 1},
            target_label=f"{target_value} @ {click_coords[0]},{click_coords[1]}",
        )
        return actions

    if hotkey and type_text:
        if target_window or target_app:
            add_action("focus_window", f"Focus {target_value}", arguments=focus_arguments)
        add_action(
            "press_hotkey",
            f"Press {hotkey}",
            arguments={"keys": hotkey},
            target_label=f"{target_value} / {hotkey}",
        )
        add_action(
            "type_text",
            f"Type text into {target_value}",
            arguments={"text": type_text},
            target_label=f"{target_value} / text input",
        )
        return actions

    if hotkey:
        if target_window or target_app:
            add_action("focus_window", f"Focus {target_value}", arguments=focus_arguments)
        add_action(
            "press_hotkey",
            f"Press {hotkey}",
            arguments={"keys": hotkey},
            target_label=f"{target_value} / {hotkey}",
        )
        return actions

    if type_text:
        if target_window or target_app:
            add_action("focus_window", f"Focus {target_value}", arguments=focus_arguments)
        add_action(
            "type_text",
            f"Type text into {target_value}",
            arguments={"text": type_text},
            target_label=f"{target_value} / text input",
        )
        return actions

    if any(token in lowered for token in ["focus", "switch window", "activate", "bring to front"]) and (target_window or target_app):
        add_action("focus_window", f"Focus {target_value}", arguments=focus_arguments)
        return actions

    if target_window:
        add_action("focus_window", "Prepare desktop control", arguments=focus_arguments)
    elif target_app:
        add_action("launch_app", "Prepare desktop control", arguments={"target_app": target_app})
    return actions


async def _run_desktop_probe(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    parent_execution: RuntimeExecution,
    mode: ChatMode,
    title: str,
    summary: str,
    actions: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="desktop_inspect",
        provider_id=conversation.provider_id if conversation else None,
        model_id=conversation.model_id if conversation else None,
        provider_connection_id=conversation.provider_connection_id if conversation else None,
        resolved_model_name=conversation.model_name if conversation else None,
        resolved_base_url=conversation.provider_connection.base_url if conversation and conversation.provider_connection else None,
        conversation_id=conversation.id if conversation else None,
        prompt_preview=title,
        command_preview=str(actions),
        details_json={"parent_execution_id": parent_execution.id, "mode": mode, "planned_actions": actions},
    )
    try:
        await mark_runtime_running(session, execution)
        result = await dispatch_desktop_execution(
            session,
            workspace=workspace,
            user=user,
            execution=execution,
            actions=actions,
            session_mode="reuse",
            require_read_only=True,
        )
        step_status = str(result.get("status") or ("degraded" if result.get("warnings") else "succeeded"))
        warnings = [str(item).strip() for item in (result.get("warnings") or []) if str(item).strip()]
        output_excerpt = result.get("extracted_text") or str(result.get("active_window") or result.get("system_info") or "Desktop probe completed")
        if warnings:
            output_excerpt = f"{output_excerpt}\n\nWarnings:\n- " + "\n- ".join(warnings[:3])
        step_summary = summary if not warnings else f"{summary} {' '.join(warnings[:2])}".strip()
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=output_excerpt[:400],
            details_json={
                "parent_execution_id": parent_execution.id,
                "mode": mode,
                "actions": actions,
                "active_window": result.get("active_window"),
                "system_info": result.get("system_info"),
                "warnings": warnings,
                "environment": result.get("environment"),
                "trace_summary": {
                    "headline": title,
                    "summary": step_summary,
                    "status": step_status,
                    "timeline_count": 1,
                    "has_artifacts": bool(result.get("artifacts_json")),
                },
            },
            artifacts_json=result.get("artifacts_json") or [],
        )
        step = {
            "kind": "desktop",
            "title": title,
            "summary": step_summary,
            "status": step_status,
            "runtime_execution_id": execution.id,
            "runtime_session_id": result.get("runtime_session_id"),
            "command_preview": actions,
            "output_excerpt": output_excerpt,
            "artifact_summaries": result.get("artifacts_json") or [],
            "label": (result.get("active_window") or {}).get("title") if isinstance(result.get("active_window"), dict) else None,
            "current_url": None,
            "is_read_only": True,
            "warnings": warnings,
        }
        evidence = {
            "title": title,
            "type": "desktop_capture",
            "runtime_execution_id": execution.id,
            "content": output_excerpt,
            "label": (result.get("active_window") or {}).get("title") if isinstance(result.get("active_window"), dict) else None,
            "artifact_summaries": result.get("artifacts_json") or [],
            "stderr_excerpt": "\n".join(warnings[:3]) if warnings else None,
            "metadata": {
                "active_window": result.get("active_window"),
                "system_info": result.get("system_info"),
                "processes": result.get("processes"),
                "windows": result.get("windows"),
                "warnings": warnings,
                "environment": result.get("environment"),
            },
        }
        desktop_artifacts = list(result.get("artifacts_json") or [])
        return step, evidence, desktop_artifacts
    except Exception as exc:
        await mark_runtime_failed(
            session,
            execution,
            error_message=str(exc),
            details_json={"parent_execution_id": parent_execution.id, "mode": mode, "actions": actions},
        )
        step = {
            "kind": "desktop",
            "title": title,
            "summary": summary,
            "status": "failed",
            "runtime_execution_id": execution.id,
            "runtime_session_id": None,
            "command_preview": actions,
            "output_excerpt": str(exc),
            "artifact_summaries": [],
            "is_read_only": True,
        }
        evidence = {
            "title": title,
            "type": "desktop_capture",
            "runtime_execution_id": execution.id,
            "content": str(exc),
            "stderr_excerpt": str(exc),
            "artifact_summaries": [],
        }
        return step, evidence, []


def build_desktop_operator_response_prompt(trace: dict[str, Any]) -> str:
    approval = trace.get("desktop_action_approval") or {}
    return "\n".join(
        [
            "You are DreamAxis in desktop operator mode.",
            "Write in concise operator language with these sections: Intent / plan, Grounded target, What ran, What was found, Recommended next step.",
            f"Active mode: {trace.get('mode')}",
            f"Grounding summary: {(trace.get('grounding_summary') or {}).get('summary', 'No grounding summary.')}",
            f"Approval summary: {approval.get('summary', 'No approval required.')}",
            "Base every claim on the provided execution evidence or runtime inventory.",
        ]
    )


def build_desktop_operator_fallback_response(trace: dict[str, Any]) -> str:
    grounded = trace.get("primary_grounded_target") or {}
    approval = trace.get("desktop_action_approval") or {}
    evidence = trace.get("evidence_items") or trace.get("evidence") or []
    lines = [
        "## Intent / plan",
        *[f"- {item}" for item in trace.get("intent_plan") or []],
        "",
        "## Grounded target",
        f"- {grounded.get('label', 'Target')}: {grounded.get('value', '--')}",
        "",
        "## What ran",
    ]
    if trace.get("steps"):
        lines.extend([f"- {step.get('title')}: {step.get('summary')}" for step in trace.get("steps") or []])
    else:
        lines.append(f"- {approval.get('summary', 'No desktop probes executed in this turn.')} ")
    lines.extend(["", "## What was found"])
    if evidence:
        lines.extend([f"- {item.get('title')}: {item.get('content') or item.get('label') or '--'}" for item in evidence[:3]])
    else:
        lines.append("- No runtime evidence captured yet.")
    lines.extend(["", "## Recommended next step"])
    for item in trace.get("recommended_next_actions") or []:
        lines.append(f"- {item.get('label')}: {item.get('reason') or ''}".rstrip())
    return "\n".join(lines)


async def review_desktop_action_approval(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    parent_execution: RuntimeExecution,
    decision: str,
) -> tuple[RuntimeExecution, RuntimeExecution | None, dict[str, Any]]:
    normalized_decision = decision.strip().lower()
    if normalized_decision not in {"approved", "denied"}:
        raise ValueError("Desktop approval decision must be either 'approved' or 'denied'.")

    trace = ((parent_execution.details_json or {}).get("execution_trace") if isinstance(parent_execution.details_json, dict) else None) or {}
    if not isinstance(trace, dict):
        raise ValueError("Runtime execution does not contain a desktop execution trace.")
    if trace.get("mode") != "operate_desktop":
        raise ValueError("This runtime execution is not an operate_desktop turn.")

    approval = trace.get("desktop_action_approval")
    if not isinstance(approval, dict):
        raise ValueError("This desktop turn does not have an approval gate.")

    current_status = str(approval.get("status") or "")
    if current_status == normalized_decision:
        return parent_execution, None, trace
    if current_status not in {"approval_required", "approved", "denied"}:
        raise ValueError("This desktop approval is not in a reviewable state.")

    requested_actions = _dict_list(trace.get("requested_desktop_actions"))
    if not requested_actions:
        raise ValueError("No requested desktop actions were stored for this approval turn.")

    target_value = (
        (trace.get("primary_grounded_target") or {}).get("value")
        if isinstance(trace.get("primary_grounded_target"), dict)
        else None
    ) or requested_actions[0].get("target_label") or "desktop"

    timeline = _dict_list(trace.get("actual_events") or trace.get("timeline"))
    steps = _dict_list(trace.get("steps"))
    evidence_items = _dict_list(trace.get("evidence_items") or trace.get("evidence"))
    runtime_execution_ids = [str(item) for item in (trace.get("runtime_execution_ids") or []) if str(item).strip()]
    child_execution_ids = [str(item) for item in (trace.get("child_execution_ids") or []) if str(item).strip()]
    desktop_artifacts = _safe_artifacts(trace.get("desktop_artifacts") or trace.get("artifact_summaries"))
    desktop_action_steps = _dict_list(trace.get("desktop_action_steps"))

    if normalized_decision == "denied":
        approval["status"] = "denied"
        approval["summary"] = f"DreamAxis did not execute the requested desktop action for `{target_value}`."
        approval["next_step_label"] = "Request a different action"
        approval["reason"] = "The desktop operator kept the action blocked because the approval was denied."
        for item in desktop_action_steps:
            item["status"] = "blocked"
            item["summary"] = "User denied this desktop action before execution."
        trace["workflow_stage"] = "complete"
        trace["desktop_action_steps"] = desktop_action_steps
        trace["desktop_action_approval"] = approval
        trace["recommended_next_actions"] = [
            {
                "label": "Request a different action or inspect again",
                "reason": "The previous desktop action was denied, so DreamAxis left the desktop unchanged.",
            }
        ]
        timeline.append(
            build_annotation(
                annotation_id=f"desktop-approval-denied-{len(timeline) + 1}",
                kind="approval_required",
                title="Desktop approval denied",
                summary=approval["summary"],
                status="failed",
                source_layer="chat",
                target_label=str(target_value),
                payload_preview={"decision": "denied", "requested_actions": requested_actions},
            )
        )
        trace["actual_events"] = timeline
        trace["timeline"] = timeline
        trace["trace_summary"] = {
            "headline": "Operate desktop / Approval denied",
            "summary": approval["summary"],
            "status": "succeeded",
            "timeline_count": len(timeline),
            "has_artifacts": bool(desktop_artifacts),
        }
        updated_parent = await _persist_parent_trace(session, execution=parent_execution, trace=trace)
        return updated_parent, None, trace

    approval["status"] = "approved"
    approval["summary"] = f"DreamAxis is executing the approved desktop action for `{target_value}`."
    approval["next_step_label"] = "Review action evidence"
    approval["reason"] = "The requested desktop action was explicitly approved and is now part of the audit trail."
    for item in desktop_action_steps:
        item["status"] = "approved"
        item["summary"] = "Action approved and queued for execution."
    trace["desktop_action_steps"] = desktop_action_steps
    trace["desktop_action_approval"] = approval
    trace["workflow_stage"] = "execution"
    timeline.append(
        build_annotation(
            annotation_id=f"desktop-approval-approved-{len(timeline) + 1}",
            kind="approval_required",
            title="Desktop approval granted",
            summary=approval["summary"],
            status="running",
            source_layer="chat",
            target_label=str(target_value),
            payload_preview={"decision": "approved", "requested_actions": requested_actions},
        )
    )
    trace["actual_events"] = timeline
    trace["timeline"] = timeline
    await _persist_parent_trace(session, execution=parent_execution, trace=trace)

    child_execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="desktop_operate",
        provider_id=parent_execution.provider_id,
        model_id=parent_execution.model_id,
        provider_connection_id=parent_execution.provider_connection_id,
        resolved_model_name=parent_execution.resolved_model_name,
        resolved_base_url=parent_execution.resolved_base_url,
        conversation_id=parent_execution.conversation_id,
        prompt_preview=f"Approved desktop action / {target_value}",
        command_preview=str(_normalize_operate_actions(requested_actions)),
        details_json={
            "parent_execution_id": parent_execution.id,
            "mode": trace.get("mode"),
            "approval_decision": "approved",
            "requested_actions": requested_actions,
        },
    )
    await mark_runtime_running(session, child_execution)

    try:
        result = await dispatch_desktop_execution(
            session,
            workspace=workspace,
            user=user,
            execution=child_execution,
            actions=requested_actions,
            session_mode="reuse",
            require_read_only=False,
        )
        summary, warnings = _summarize_desktop_action_result(result, requested_actions=requested_actions)
        child_status = str(result.get("status") or ("degraded" if warnings else "succeeded"))
        response_preview = summary if not warnings else f"{summary}\nWarnings:\n- " + "\n- ".join(warnings[:3])
        child_details = {
            "parent_execution_id": parent_execution.id,
            "mode": trace.get("mode"),
            "approval_decision": "approved",
            "requested_actions": requested_actions,
            "active_window": result.get("active_window"),
            "focused_window": result.get("focused_window"),
            "warnings": warnings,
            "environment": result.get("environment"),
            "action_results": _dict_list(result.get("action_results")),
            "trace_summary": {
                "headline": "Approved desktop action",
                "summary": summary,
                "status": child_status,
                "timeline_count": 1,
                "has_artifacts": bool(result.get("artifacts_json")),
            },
        }
        await mark_runtime_succeeded(
            session,
            child_execution,
            response_preview=response_preview[:400],
            details_json=child_details,
            artifacts_json=_safe_artifacts(result.get("artifacts_json")),
        )

        step = _build_action_result_step(
            child_execution=child_execution,
            requested_actions=requested_actions,
            result=result,
            status=child_status,
            summary=summary,
            warnings=warnings,
        )
        evidence = _build_action_result_evidence(
            child_execution=child_execution,
            requested_actions=requested_actions,
            result=result,
            summary=summary,
            warnings=warnings,
        )
        steps.append(step)
        evidence_items.append(evidence)
        if child_execution.id not in child_execution_ids:
            child_execution_ids.append(child_execution.id)
        if child_execution.id not in runtime_execution_ids:
            runtime_execution_ids.append(child_execution.id)
        desktop_artifacts.extend(_safe_artifacts(result.get("artifacts_json")))
        for item in desktop_action_steps:
            item["status"] = "executed" if child_status != "failed" else "blocked"
            item["summary"] = summary

        trace["desktop_action_steps"] = desktop_action_steps
        trace["steps"] = steps
        trace["evidence"] = evidence_items
        trace["evidence_items"] = evidence_items
        trace["child_execution_ids"] = child_execution_ids
        trace["runtime_execution_ids"] = runtime_execution_ids
        trace["desktop_artifacts"] = desktop_artifacts
        trace["artifact_summaries"] = desktop_artifacts
        trace["workflow_stage"] = "complete"
        trace["failure_summary"] = summary if child_status == "failed" else (warnings[0] if child_status == "degraded" and warnings else None)
        trace["failure_classification"] = "browser_or_runtime_failure" if child_status == "failed" else ("desktop_runtime_degraded" if child_status == "degraded" else None)
        trace["stderr_highlights"] = warnings[:3] if warnings else []
        trace["grounded_next_step_reasoning"] = (
            [
                "The action completed but the runtime reported warnings.",
                "Review the captured artifact and rerun a verify_desktop turn before issuing another state-changing action.",
            ]
            if child_status == "degraded"
            else [
                "The approved action executed against the grounded desktop target.",
                "Inspect the resulting window or screenshot evidence before issuing the next action.",
            ]
        )
        trace["recommended_next_actions"] = (
            [
                {
                    "label": "Open the child desktop runtime",
                    "reason": summary,
                },
                {
                    "label": "Run verify_desktop on the same target",
                    "reason": "Capture a fresh post-action screenshot and OCR summary before continuing.",
                },
            ]
            if child_status != "failed"
            else [
                {
                    "label": "Inspect the failed desktop runtime execution",
                    "reason": summary,
                },
                {
                    "label": "Retry with a narrower target",
                    "reason": "Use the grounded target and failure details to issue a safer follow-up action.",
                },
            ]
        )
        timeline.append(
            build_annotation(
                annotation_id=f"desktop-approved-step-{len(timeline) + 1}",
                kind="desktop_action",
                title="Approved desktop action executed",
                summary=summary,
                status=child_status,
                source_layer="runtime",
                runtime_execution_id=child_execution.id,
                runtime_session_id=result.get("runtime_session_id"),
                target_label=str(target_value),
                payload_preview={
                    "requested_actions": requested_actions,
                    "action_results": _dict_list(result.get("action_results")),
                },
            )
        )
        trace["actual_events"] = timeline
        trace["timeline"] = timeline
        trace["trace_summary"] = {
            "headline": "Operate desktop / Approved action",
            "summary": summary,
            "status": child_status,
            "timeline_count": len(timeline),
            "has_artifacts": bool(desktop_artifacts),
        }
        updated_parent = await _persist_parent_trace(session, execution=parent_execution, trace=trace)
        return updated_parent, child_execution, trace
    except Exception as exc:
        await mark_runtime_failed(
            session,
            child_execution,
            error_message=str(exc),
            details_json={
                "parent_execution_id": parent_execution.id,
                "mode": trace.get("mode"),
                "approval_decision": "approved",
                "requested_actions": requested_actions,
            },
        )
        for item in desktop_action_steps:
            item["status"] = "blocked"
            item["summary"] = str(exc)
        trace["desktop_action_steps"] = desktop_action_steps
        trace["workflow_stage"] = "reflection"
        trace["failure_summary"] = str(exc)
        trace["failure_classification"] = "browser_or_runtime_failure"
        trace["stderr_highlights"] = [str(exc)]
        trace["grounded_next_step_reasoning"] = [
            "The approved desktop action failed inside the runtime worker.",
            "Inspect the child runtime execution and narrow the next operator action before retrying.",
        ]
        trace["recommended_next_actions"] = [
            {
                "label": "Open the failed desktop runtime",
                "reason": "Review the runtime error before issuing another action.",
            }
        ]
        if child_execution.id not in child_execution_ids:
            child_execution_ids.append(child_execution.id)
        if child_execution.id not in runtime_execution_ids:
            runtime_execution_ids.append(child_execution.id)
        trace["child_execution_ids"] = child_execution_ids
        trace["runtime_execution_ids"] = runtime_execution_ids
        timeline.append(
            build_annotation(
                annotation_id=f"desktop-approved-step-{len(timeline) + 1}",
                kind="desktop_action",
                title="Approved desktop action failed",
                summary=str(exc),
                status="failed",
                source_layer="runtime",
                runtime_execution_id=child_execution.id,
                target_label=str(target_value),
                payload_preview={"requested_actions": requested_actions},
            )
        )
        trace["actual_events"] = timeline
        trace["timeline"] = timeline
        trace["trace_summary"] = {
            "headline": "Operate desktop / Approved action failed",
            "summary": str(exc),
            "status": "failed",
            "timeline_count": len(timeline),
            "has_artifacts": bool(desktop_artifacts),
        }
        updated_parent = await _persist_parent_trace(session, execution=parent_execution, trace=trace)
        return updated_parent, child_execution, trace


async def collect_desktop_operator_trace(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    parent_execution: RuntimeExecution,
    prompt: str,
    mode: ChatMode | None = None,
    knowledge_sources: list[KnowledgeChunkReference] | None = None,
) -> dict[str, Any]:
    scenario_tag, router_reason, resolved_mode = infer_desktop_mode(prompt, mode)
    runtimes = await list_runtimes_for_workspace(session, workspace.id)
    desktop_runtimes = [runtime for runtime in runtimes if runtime.runtime_type == "desktop"]
    target = detect_desktop_target(prompt)
    grounded_result = resolve_desktop_target(
        prompt=prompt,
        workspace_root=str(workspace.workspace_root_path or "."),
        desktop_runtime_names=[runtime.name for runtime in desktop_runtimes],
    )
    target_value = grounded_result.target_identifier or grounded_result.context_snapshot.prompt_derived_target
    signals = build_grounding_signals(grounded_result)
    primary_target = grounded_target_from_result(grounded_result)

    requested_actions: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    desktop_artifacts: list[dict[str, Any]] = []
    child_execution_ids: list[str] = []
    probe_status = "succeeded"
    probe_warnings: list[str] = []
    planned_actions = [
        build_annotation(
            annotation_id="desktop-grounding",
            kind="grounding_selected",
            title="Desktop grounding",
            summary=f"Grounded the turn on `{target_value}` with desktop runtime awareness.",
            status="ready",
            source_layer="chat",
            target_label=target_value,
        )
    ]

    if resolved_mode in {"inspect_desktop", "verify_desktop"} and desktop_runtimes:
        actions = [
            {"action": "read_system_info"},
            {"action": "list_windows"},
            {"action": "inspect_focused_window"},
            {"action": "list_processes", "limit": 30},
        ]
        if resolved_mode == "verify_desktop":
            actions.extend([
                {"action": "capture_screen"},
                {"action": "extract_text"},
            ])
        step, evidence_item, artifacts = await _run_desktop_probe(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            parent_execution=parent_execution,
            mode=resolved_mode,
            title="Desktop state probe",
            summary="Collected current Windows state, windows, processes, and visible evidence for the grounded target.",
            actions=actions,
        )
        steps.append(step)
        evidence.append(evidence_item)
        child_execution_ids.extend([step.get("runtime_execution_id")] if step.get("runtime_execution_id") else [])
        desktop_artifacts.extend(artifacts)
        requested_actions = actions
        probe_status = str(step.get("status") or "succeeded")
        probe_warnings = [str(item).strip() for item in (step.get("warnings") or []) if str(item).strip()]
    elif resolved_mode == "operate_desktop":
        requested_actions = _build_requested_actions(prompt, target)
        evidence.append(
            {
                "title": "Approval gate",
                "type": "desktop_capture",
                "content": f"DreamAxis prepared {len(requested_actions)} gated desktop action(s) for `{target_value}` but did not execute them.",
                "label": target_value,
                "metadata": {"requested_actions": requested_actions},
            }
        )
    else:
        evidence.append(
            {
                "title": "Desktop runtime unavailable",
                "type": "desktop_capture",
                "content": "No desktop runtime is online yet, so DreamAxis stayed in planning-only desktop mode.",
                "label": "runtime offline",
            }
        )

    approval = {
        "status": "approval_required" if resolved_mode == "operate_desktop" else "not_required",
        "summary": (
            f"Approval required before DreamAxis can change `{target_value}`."
            if resolved_mode == "operate_desktop"
            else "No explicit approval is needed for read-only desktop inspection."
        ),
        "requested_actions": requested_actions if resolved_mode == "operate_desktop" else [],
        "next_step_label": "Confirm desktop action" if resolved_mode == "operate_desktop" else "Review captured evidence",
        "reason": "Desktop state-changing actions are gated by default." if resolved_mode == "operate_desktop" else "This turn only used or prepared read-only desktop inspection.",
    }

    reflection_triggered = resolved_mode != "operate_desktop" and (not desktop_runtimes or probe_status in {"failed", "degraded"})
    probe_degraded = probe_status == "degraded"
    probe_failed = probe_status == "failed"
    failure_summary = None
    failure_classification = None
    primary_failure_target = None
    stderr_highlights: list[str] = []
    grounded_next_step_reasoning: list[str] = []

    if not desktop_runtimes and resolved_mode != "operate_desktop":
        failure_summary = "Desktop runtime is offline, so DreamAxis could not collect live Windows evidence yet."
        failure_classification = "desktop_runtime_missing"
        primary_failure_target = target_value
        grounded_next_step_reasoning = [
            "No desktop runtime host is currently online for this workspace.",
            "Start the desktop runtime host before attempting another live desktop verification pass.",
        ]
    elif probe_degraded:
        failure_summary = probe_warnings[0] if probe_warnings else "The desktop runtime responded, but the current host cannot provide full Windows desktop evidence."
        failure_classification = "desktop_runtime_degraded"
        primary_failure_target = target_value
        stderr_highlights = probe_warnings[:3]
        grounded_next_step_reasoning = [
            "The current runtime can register and answer requests, but it is missing native Windows desktop capabilities.",
            "Move the desktop worker to a native Windows host, then rerun the same verify_desktop or inspect_desktop turn.",
        ]
    elif probe_failed:
        failure_summary = steps[0].get("output_excerpt") if steps else "Desktop probe failed before returning evidence."
        failure_classification = "browser_or_runtime_failure"
        primary_failure_target = target_value
        stderr_highlights = [str(failure_summary)] if failure_summary else []
        grounded_next_step_reasoning = [
            "The desktop probe failed inside the runtime worker.",
            "Inspect the child desktop runtime execution before retrying the operator turn.",
        ]

    reflection_summary = {
        "triggered": reflection_triggered,
        "summary": (
            "Desktop runtime is offline, so narrow the next action to starting the Windows desktop worker first."
            if not desktop_runtimes and resolved_mode != "operate_desktop"
            else (
                "The desktop runtime answered in a degraded state, so narrow the next action to moving the worker onto a native Windows host."
                if probe_degraded
                else (
                    "The desktop probe failed, so narrow the next action to inspecting the child runtime execution before retrying."
                    if probe_failed
                    else "No extra reflection pass was needed beyond the grounded desktop lane."
                )
            )
            if reflection_triggered
            else "No extra reflection pass was needed beyond the grounded desktop lane."
        ),
        "reason": (
            "A desktop runtime host is required for live Windows inspection."
            if not desktop_runtimes and resolved_mode != "operate_desktop"
            else (probe_warnings[0] if probe_degraded and probe_warnings else ("The desktop runtime child execution failed." if probe_failed else None))
        )
        if reflection_triggered
        else None,
        "next_probe": (
            "Start desktop runtime and rerun verify_desktop"
            if not desktop_runtimes and resolved_mode != "operate_desktop"
            else ("Start the desktop worker on the Windows host and rerun verify_desktop" if probe_degraded else ("Open the child runtime execution and inspect the worker diagnostics" if probe_failed else None))
        )
        if reflection_triggered
        else None,
        "confidence": 0.82 if probe_degraded else (0.78 if reflection_triggered else 0.68),
    }

    recommended_next_actions = []
    if resolved_mode == "operate_desktop":
        recommended_next_actions.append({
            "label": "Confirm desktop action",
            "reason": "Review the target and requested steps, then approve to execute the gated desktop action sequence.",
        })
    elif not desktop_runtimes:
        recommended_next_actions.append({
            "label": "Start a desktop runtime worker",
            "reason": "A Windows desktop host is required before DreamAxis can capture live screen and window evidence.",
        })
    elif probe_degraded:
        recommended_next_actions.append({
            "label": "Move the desktop worker to a native Windows host",
            "reason": failure_summary or "The current runtime can register, but it cannot capture live Windows desktop evidence in this environment.",
        })
        recommended_next_actions.append({
            "label": "Rerun verify_desktop after the worker move",
            "reason": "Use the same grounded target once the host can enumerate windows and capture screenshots.",
        })
    elif probe_failed:
        recommended_next_actions.append({
            "label": "Inspect the child desktop runtime",
            "reason": failure_summary or "Review the failed child runtime execution before retrying the desktop operator turn.",
        })
    else:
        recommended_next_actions.append({
            "label": "Review the active window evidence",
            "reason": "Use the captured window/process/screenshot evidence to decide the next operator action.",
        })

    timeline = [
        *planned_actions,
        *([
            build_annotation(
                annotation_id="desktop-approval",
                kind="approval_required",
                title="Approval gate",
                summary=approval["summary"],
                status="ready" if resolved_mode == "operate_desktop" else "succeeded",
                source_layer="chat",
                target_label=target_value,
                payload_preview={"requested_actions": requested_actions} if requested_actions else {"mode": resolved_mode},
            )
        ] if approval else []),
        *[
            build_annotation(
                annotation_id=f"desktop-step-{index}",
                kind="desktop_probe",
                title=step.get("title") or "Desktop probe",
                summary=step.get("summary") or "Collected desktop evidence.",
                status=step.get("status") or "succeeded",
                source_layer="runtime",
                runtime_execution_id=step.get("runtime_execution_id"),
                runtime_session_id=step.get("runtime_session_id"),
                target_label=target_value,
            )
            for index, step in enumerate(steps, start=1)
        ],
        build_annotation(
            annotation_id="desktop-reflection",
            kind="reflection_follow_up",
            title="Reflection",
            summary=reflection_summary["summary"],
            status="ready" if reflection_summary["triggered"] else "succeeded",
            source_layer="chat",
            target_label=reflection_summary.get("next_probe") or target_value,
        ),
    ]

    status = "failed" if probe_failed else ("degraded" if failure_summary else "succeeded")
    return {
        "mode": resolved_mode,
        "mode_summary": {
            "active_mode": resolved_mode,
            "requested_mode": mode,
            "inferred_from": "user_selection" if mode else "auto_router",
            "rationale": router_reason,
        },
        "scenario_tag": scenario_tag,
        "scenario_label": "Desktop operator",
        "router_reason": router_reason,
        "workflow_stage": "approval" if resolved_mode == "operate_desktop" else ("reflection" if reflection_triggered else "execution"),
        "intent_plan": [
            "Ground the request against the current Windows desktop surface.",
            "Use read-only probes or prepare a gated desktop action plan.",
            "Return evidence first and keep any state-changing action behind approval.",
        ],
        "grounding_summary": {
            "headline": "Desktop grounding",
            "summary": f"Grounded the turn on `{target_value}` with desktop runtime status `{('online' if desktop_runtimes else 'offline')}`.",
            "signals": signals,
        },
        "desktop_grounding_summary": {
            "headline": "Desktop grounding",
            "summary": f"Grounded the turn on `{target_value}` with desktop runtime status `{('online' if desktop_runtimes else 'offline')}`.",
            "signals": signals,
        },
        "grounded_targets": [primary_target],
        "primary_grounded_target": primary_target,
        "reflection_summary": reflection_summary,
        "reflection_reason": reflection_summary.get("reason"),
        "reflection_next_probe": reflection_summary.get("next_probe"),
        "steps": steps,
        "evidence": evidence,
        "evidence_items": evidence,
        "execution_bundle_id": parent_execution.id,
        "child_execution_ids": child_execution_ids,
        "desktop_action_approval": approval,
        "requested_desktop_actions": requested_actions if isinstance(requested_actions, list) else [],
        "desktop_action_steps": [
            {
                "id": item.get("id") or f"step-{index}",
                "action": item.get("action") or "desktop",
                "title": item.get("title") or "Desktop action",
                "status": "planned" if resolved_mode == "operate_desktop" else "executed",
                "target_label": item.get("target_label") if isinstance(item, dict) else None,
                "summary": item.get("risk_note") if isinstance(item, dict) else None,
            }
            for index, item in enumerate(requested_actions if isinstance(requested_actions, list) else [], start=1)
        ],
        "machine_summary": {"status": "ready" if desktop_runtimes else "degraded", "desktop_runtime": "online" if desktop_runtimes else "offline"},
        "workspace_readiness": {"status": "ready" if desktop_runtimes else "degraded", "workspace_id": workspace.id, "workspace_name": workspace.name},
        "install_guidance": (["Start the desktop runtime worker to enable live Windows inspection."] if not desktop_runtimes else []),
        "recommended_next_actions": recommended_next_actions,
        "runtime_execution_ids": child_execution_ids,
        "artifact_summaries": desktop_artifacts,
        "desktop_artifacts": desktop_artifacts,
        "primary_failure_target": primary_failure_target,
        "failure_summary": failure_summary,
        "failure_classification": failure_classification,
        "stderr_highlights": stderr_highlights,
        "grounded_next_step_reasoning": grounded_next_step_reasoning if grounded_next_step_reasoning else ["Use the grounded desktop evidence to decide whether to verify again or request a gated action."],
        "planned_actions": planned_actions,
        "actual_events": timeline,
        "timeline": timeline,
        "proposal": None,
        "trace_summary": {
            "headline": f"{DESKTOP_MODE_LABELS[resolved_mode]} / Desktop operator",
            "summary": router_reason,
            "status": status,
            "timeline_count": len(timeline),
            "has_artifacts": bool(desktop_artifacts),
        },
        "safety_summary": {
            "mode": "desktop_gated_actions",
            "blocked_write_actions": True,
            "approval_required_for_state_change": True,
            "proposal_only": False,
        },
    }
