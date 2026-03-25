from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operator_plan import OperatorPlan
from app.services.assistant_service import generate_entity_id


BUILTIN_OPERATOR_TEMPLATES: list[dict[str, Any]] = [
    {
        "slug": "inspect-active-desktop",
        "title": "Inspect active desktop",
        "description": "Capture the active desktop surface, windows, processes, and focus state.",
        "mode": "inspect_desktop",
        "prompt": "Inspect the active desktop, summarize the focused window, list the main windows, and report system state.",
        "tags": ["desktop", "inspect", "grounding"],
    },
    {
        "slug": "verify-browser-surface",
        "title": "Verify browser surface",
        "description": "Focus browser verification with screenshot, OCR, and route-readable evidence.",
        "mode": "verify_desktop",
        "prompt": "Verify the current browser surface, capture a screenshot, extract visible text, and summarize what is currently open.",
        "tags": ["browser", "verify", "ocr"],
    },
    {
        "slug": "focus-terminal-capture",
        "title": "Focus terminal and capture output",
        "description": "Bring Terminal forward and capture the visible shell state.",
        "mode": "operate_desktop",
        "prompt": "Focus Windows Terminal, inspect the visible shell output, and capture the active terminal surface for audit.",
        "tags": ["terminal", "focus", "capture"],
    },
    {
        "slug": "focus-vscode-summary",
        "title": "Focus VS Code and summarize state",
        "description": "Bring VS Code into focus and summarize the visible workspace/editor state.",
        "mode": "operate_desktop",
        "prompt": "Focus Visual Studio Code and summarize the current workspace, visible editor, and window state.",
        "tags": ["vscode", "editor", "workspace"],
    },
    {
        "slug": "browser-terminal-vscode-triad",
        "title": "Browser + Terminal + VS Code triad",
        "description": "Collect a grounded summary across browser, terminal, and editor surfaces.",
        "mode": "verify_desktop",
        "prompt": "Verify the current browser, terminal, and Visual Studio Code surfaces and summarize the active state across all three.",
        "tags": ["browser", "terminal", "vscode", "triad"],
    },
]


def list_builtin_operator_templates() -> list[dict[str, Any]]:
    return [dict(item) for item in BUILTIN_OPERATOR_TEMPLATES]


def resolve_operator_template(template_slug: str | None) -> dict[str, Any] | None:
    if not template_slug:
        return None
    for item in BUILTIN_OPERATOR_TEMPLATES:
        if item["slug"] == template_slug:
            return dict(item)
    return None


def resolve_operator_plan_input(
    *,
    prompt: str | None,
    mode: str | None,
    template_slug: str | None,
    title: str | None = None,
) -> dict[str, str | None]:
    template = resolve_operator_template(template_slug)
    if template_slug and template is None:
        raise HTTPException(status_code=404, detail="Operator template not found")

    resolved_prompt = (prompt or "").strip() or (template.get("prompt") if template else "")
    if not resolved_prompt:
        raise HTTPException(status_code=400, detail="Operator plan prompt is required")

    resolved_mode = (mode or (template.get("mode") if template else None) or "inspect_desktop").strip()
    resolved_title = (title or "").strip() or (template.get("title") if template else None) or resolved_prompt[:80]
    return {
        "prompt": resolved_prompt,
        "mode": resolved_mode,
        "title": resolved_title,
        "template_slug": template_slug or (template.get("slug") if template else None),
    }


async def get_operator_plan_or_404(session: AsyncSession, *, operator_plan_id: str, user_id: str) -> OperatorPlan:
    plan = await session.scalar(
        select(OperatorPlan).where(OperatorPlan.id == operator_plan_id, OperatorPlan.created_by_id == user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Operator plan not found")
    return plan


async def get_operator_plan_by_parent_execution(
    session: AsyncSession, *, parent_execution_id: str, user_id: str
) -> OperatorPlan | None:
    return await session.scalar(
        select(OperatorPlan).where(
            OperatorPlan.parent_execution_id == parent_execution_id,
            OperatorPlan.created_by_id == user_id,
        )
    )


def _derive_plan_status(trace: dict[str, Any]) -> str:
    approval = trace.get("desktop_action_approval") if isinstance(trace.get("desktop_action_approval"), dict) else {}
    approval_status = str((approval or {}).get("status") or "")
    trace_summary = trace.get("trace_summary") if isinstance(trace.get("trace_summary"), dict) else {}
    workflow_stage = str(trace.get("workflow_stage") or "")
    steps = [item for item in (trace.get("steps") or []) if isinstance(item, dict)]
    if approval_status == "approval_required":
        return "awaiting_approval"
    if approval_status == "denied":
        return "blocked"
    if any(str(step.get("status") or "").lower() == "failed" for step in steps):
        return "failed"
    if trace.get("failure_summary"):
        return "failed"
    if workflow_stage in {"grounding", "execution", "reflection"} and str(trace_summary.get("status") or "") in {"running", "queued", ""}:
        return "running"
    if str(trace_summary.get("status") or "") in {"failed", "error"}:
        return "failed"
    if workflow_stage in {"approval"}:
        return "awaiting_approval"
    return "succeeded"


def _resolve_active_step_id(trace: dict[str, Any]) -> str | None:
    steps = [item for item in (trace.get("desktop_action_steps") or trace.get("steps") or []) if isinstance(item, dict)]
    for item in steps:
        if str(item.get("status") or "").lower() in {"running", "queued", "planned", "approved", "failed"}:
            return str(item.get("id") or item.get("runtime_execution_id") or "")
    if steps:
        item = steps[-1]
        return str(item.get("id") or item.get("runtime_execution_id") or "")
    return None


def _step_verification_summary(trace: dict[str, Any]) -> str | None:
    if trace.get("failure_summary"):
        return str(trace.get("failure_summary"))
    steps = [item for item in (trace.get("steps") or []) if isinstance(item, dict)]
    if steps:
        return str(steps[-1].get("summary") or steps[-1].get("output_excerpt") or "")
    summary = trace.get("trace_summary")
    if isinstance(summary, dict):
        return str(summary.get("summary") or "")
    return None


def _pending_approval_count(trace: dict[str, Any]) -> int:
    approval = trace.get("desktop_action_approval") if isinstance(trace.get("desktop_action_approval"), dict) else {}
    if str((approval or {}).get("status") or "") != "approval_required":
        return 0
    actions = [item for item in (trace.get("requested_desktop_actions") or []) if isinstance(item, dict)]
    return len(actions)


def inject_operator_plan_trace_fields(trace: dict[str, Any], plan: OperatorPlan) -> dict[str, Any]:
    mutated = dict(trace)
    mutated["operator_plan_id"] = plan.id
    mutated["operator_plan_status"] = plan.status
    mutated["operator_stage"] = plan.operator_stage
    mutated["active_step_id"] = _resolve_active_step_id(mutated)
    mutated["pending_approval_count"] = plan.pending_approval_count
    mutated["latest_artifact_summaries"] = list(plan.artifacts_json or [])
    mutated["step_verification_summary"] = _step_verification_summary(mutated)
    return mutated


async def sync_operator_plan_from_trace(
    session: AsyncSession,
    *,
    workspace_id: str,
    created_by_id: str,
    requested_prompt: str,
    trace: dict[str, Any],
    parent_execution_id: str | None,
    conversation_id: str | None = None,
    operator_plan_id: str | None = None,
    template_slug: str | None = None,
    title_override: str | None = None,
) -> tuple[OperatorPlan, dict[str, Any]]:
    plan = None
    if operator_plan_id:
        plan = await session.scalar(
            select(OperatorPlan).where(OperatorPlan.id == operator_plan_id, OperatorPlan.created_by_id == created_by_id)
        )
    if plan is None and parent_execution_id:
        plan = await get_operator_plan_by_parent_execution(
            session, parent_execution_id=parent_execution_id, user_id=created_by_id
        )

    primary_grounded_target = trace.get("primary_grounded_target") if isinstance(trace.get("primary_grounded_target"), dict) else {}
    title = (
        (title_override or "").strip()
        or str((trace.get("trace_summary") or {}).get("headline") or "").strip()
        or str(primary_grounded_target.get("value") or "").strip()
        or requested_prompt[:80]
    )

    if plan is None:
        plan = OperatorPlan(
            id=generate_entity_id("oplan"),
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            parent_execution_id=parent_execution_id,
            created_by_id=created_by_id,
            title=title,
            mode=str(trace.get("mode") or "inspect_desktop"),
            status="queued",
            operator_stage=str(trace.get("workflow_stage") or "grounding"),
            requested_prompt=requested_prompt,
            template_slug=template_slug,
        )
        session.add(plan)

    plan.conversation_id = conversation_id
    plan.parent_execution_id = parent_execution_id
    plan.title = title
    plan.mode = str(trace.get("mode") or plan.mode or "inspect_desktop")
    plan.operator_stage = str(trace.get("workflow_stage") or plan.operator_stage or "grounding")
    plan.status = _derive_plan_status(trace)
    plan.requested_prompt = requested_prompt
    plan.template_slug = template_slug or plan.template_slug
    plan.primary_target_label = str(primary_grounded_target.get("label") or "") or None
    plan.primary_target_value = str(primary_grounded_target.get("value") or "") or None
    plan.pending_approval_count = _pending_approval_count(trace)
    plan.summary_json = (trace.get("trace_summary") if isinstance(trace.get("trace_summary"), dict) else None) or None
    plan.steps_json = [item for item in (trace.get("steps") or []) if isinstance(item, dict)] or []
    approval = trace.get("desktop_action_approval") if isinstance(trace.get("desktop_action_approval"), dict) else None
    plan.approvals_json = [approval] if approval else []
    plan.artifacts_json = [item for item in (trace.get("artifact_summaries") or trace.get("desktop_artifacts") or []) if isinstance(item, dict)] or []
    plan.child_execution_ids_json = [str(item) for item in (trace.get("child_execution_ids") or []) if str(item).strip()] or []
    plan.last_failure_summary = str(trace.get("failure_summary") or "") or None
    await session.commit()
    await session.refresh(plan)

    updated_trace = inject_operator_plan_trace_fields(trace, plan)
    plan.trace_json = updated_trace
    await session.commit()
    await session.refresh(plan)
    return plan, updated_trace
