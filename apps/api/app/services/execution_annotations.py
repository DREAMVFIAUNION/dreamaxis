from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.runtime_execution import RuntimeExecution
from app.models.runtime_session_event import RuntimeSessionEvent


ANNOTATION_KIND_TITLES: dict[str, str] = {
    "plan_generated": "Plan generated",
    "doctor_checked": "Environment checked",
    "repo_scanned": "Repository scanned",
    "file_read": "File read",
    "code_searched": "Code searched",
    "command_started": "Command started",
    "command_finished": "Command finished",
    "browser_opened": "Browser opened",
    "browser_action": "Browser action",
    "artifact_captured": "Artifact captured",
    "knowledge_retrieved": "Knowledge retrieved",
    "model_called": "Model called",
    "message_composed": "Message composed",
    "execution_failed": "Execution failed",
    "next_action_suggested": "Next action suggested",
    "session_created": "Session created",
    "session_closed": "Session closed",
}


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def build_annotation(
    *,
    annotation_id: str,
    kind: str,
    title: str | None = None,
    summary: str | None = None,
    status: str = "ready",
    timestamp: datetime | None = None,
    source_layer: str = "runtime",
    runtime_execution_id: str | None = None,
    runtime_session_id: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    payload_preview: dict[str, Any] | str | None = None,
    raw_payload: dict[str, Any] | None = None,
    target_label: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "id": annotation_id,
        "kind": kind,
        "title": title or ANNOTATION_KIND_TITLES.get(kind) or kind.replace("_", " ").title(),
        "summary": summary or "",
        "status": status,
        "timestamp": _isoformat(timestamp),
        "source_layer": source_layer,
        "runtime_execution_id": runtime_execution_id,
        "runtime_session_id": runtime_session_id,
        "evidence_refs": evidence_refs or [],
        "payload_preview": payload_preview,
        "raw_payload": raw_payload,
        "target_label": target_label,
        "duration_ms": duration_ms,
    }


def event_to_annotation(event: RuntimeSessionEvent) -> dict[str, Any]:
    payload = event.payload_json or {}
    kind = str(payload.get("annotation_kind") or event.event_type)
    return build_annotation(
        annotation_id=event.id,
        kind=kind,
        title=payload.get("annotation_title") or event.message,
        summary=payload.get("annotation_summary") or event.message,
        status=str(payload.get("annotation_status") or "ready"),
        timestamp=event.created_at,
        source_layer=str(payload.get("source_layer") or "runtime"),
        runtime_execution_id=payload.get("execution_id"),
        runtime_session_id=event.runtime_session_id,
        evidence_refs=payload.get("evidence_refs"),
        payload_preview=payload.get("payload_preview"),
        raw_payload=payload,
        target_label=payload.get("target_label"),
        duration_ms=payload.get("duration_ms"),
    )


def timeline_from_events(events: list[RuntimeSessionEvent], *, runtime_execution_id: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for event in events:
        annotation = event_to_annotation(event)
        if runtime_execution_id and annotation.get("runtime_execution_id") != runtime_execution_id:
            continue
        items.append(annotation)
    items.sort(key=lambda item: item.get("timestamp") or "")
    return items


def summarize_execution_timeline(execution: RuntimeExecution, timeline: list[dict[str, Any]]) -> dict[str, Any]:
    failed = next((item for item in reversed(timeline) if item.get("status") == "failed"), None)
    if failed:
        headline = failed.get("title") or "Execution failed"
        summary = failed.get("summary") or execution.error_message or "Execution failed with limited details."
        status = "failed"
    elif execution.status == "succeeded":
        headline = "Execution completed"
        summary = execution.response_preview or "Execution finished successfully."
        status = "succeeded"
    elif execution.status == "running":
        headline = "Execution in progress"
        summary = execution.command_preview or execution.prompt_preview or "Execution is running."
        status = "running"
    else:
        headline = "Execution queued"
        summary = execution.command_preview or execution.prompt_preview or "Execution is waiting to run."
        status = execution.status

    return {
        "headline": headline,
        "summary": summary,
        "status": status,
        "timeline_count": len(timeline),
        "has_artifacts": bool(execution.artifacts_json),
    }


def derive_execution_timeline(execution: RuntimeExecution, session_events: list[RuntimeSessionEvent] | None = None) -> list[dict[str, Any]]:
    details = execution.details_json or {}
    trace = details.get("execution_trace") if isinstance(details, dict) else None
    if isinstance(trace, dict) and isinstance(trace.get("timeline"), list):
        return trace["timeline"]
    if session_events:
        return timeline_from_events(session_events, runtime_execution_id=execution.id)
    return []
