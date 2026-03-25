from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.operator_plan import OperatorPlan
from app.models.runtime_execution import RuntimeExecution
from app.models.user import User
from app.models.workspace import Workspace
from app.services.assistant_service import generate_entity_id
from app.services.desktop_operator import collect_desktop_operator_trace, review_desktop_action_approval
from app.services.operator_plans import inject_operator_plan_trace_fields
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded

MAX_HELPER_REFLECTIONS = 1
MAX_STEP_RETRIES = 1


def build_operator_plan_steps(*, prompt: str, mode: str, template_slug: str | None) -> list[dict[str, Any]]:
    target_prompt = prompt.strip()
    if template_slug == "browser-terminal-vscode-triad":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect browser", "prompt": "Inspect the browser surface and summarize the active page state.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect terminal", "prompt": "Inspect the active terminal surface and summarize the visible shell state.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect VS Code", "prompt": "Inspect Visual Studio Code and summarize the visible workspace/editor state.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify triad summary", "prompt": "Verify the current browser, terminal, and Visual Studio Code surfaces and summarize the active state across all three.", "status": "pending", "retry_count": 0},
        ]
    if template_slug == "verify-browser-surface":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect browser surface", "prompt": "Inspect the current browser surface and identify the active page.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify browser state", "prompt": "Verify the browser surface with screenshot and OCR evidence.", "status": "pending", "retry_count": 0},
        ]
    if template_slug == "focus-terminal-capture":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect terminal target", "prompt": "Inspect the active terminal surface and confirm the target shell window.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "operate", "mode": "operate_desktop", "title": "Focus terminal", "prompt": target_prompt, "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify terminal capture", "prompt": "Verify the terminal surface after the requested action and summarize the visible output.", "status": "pending", "retry_count": 0},
        ]
    if template_slug == "focus-vscode-summary":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect VS Code target", "prompt": "Inspect Visual Studio Code and identify the active workspace/editor.", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "operate", "mode": "operate_desktop", "title": "Focus VS Code", "prompt": target_prompt, "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify VS Code state", "prompt": "Verify the VS Code state after the requested action and summarize the visible workspace/editor.", "status": "pending", "retry_count": 0},
        ]
    if mode == "operate_desktop":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect target surface", "prompt": f"Inspect the current desktop surface before executing this request: {target_prompt}", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "operate", "mode": "operate_desktop", "title": "Execute approved action", "prompt": target_prompt, "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify result", "prompt": f"Verify the desktop after this request completes: {target_prompt}", "status": "pending", "retry_count": 0},
        ]
    if mode == "verify_desktop":
        return [
            {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect target surface", "prompt": f"Inspect the current desktop surface for this request: {target_prompt}", "status": "pending", "retry_count": 0},
            {"id": generate_entity_id("ostep"), "type": "verify", "mode": "verify_desktop", "title": "Verify target state", "prompt": target_prompt, "status": "pending", "retry_count": 0},
        ]
    return [
        {"id": generate_entity_id("ostep"), "type": "inspect", "mode": "inspect_desktop", "title": "Inspect desktop", "prompt": target_prompt, "status": "pending", "retry_count": 0},
    ]


def _step_runtime_id(step: dict[str, Any]) -> str | None:
    return str(step.get("child_execution_id") or step.get("parent_execution_id") or "").strip() or None


def _step_summary(step: dict[str, Any]) -> str:
    return str(step.get("summary") or step.get("verification_summary") or step.get("output_excerpt") or "No step summary yet.")


def _build_trace_from_plan(plan: OperatorPlan, base_trace: dict[str, Any] | None = None) -> dict[str, Any]:
    trace = dict(base_trace or plan.trace_json or {})
    steps = list(plan.steps_json or [])
    serialized_steps = [
        {
            "kind": "desktop",
            "title": str(step.get("title") or "Operator step"),
            "summary": _step_summary(step),
            "status": str(step.get("status") or "pending"),
            "runtime_execution_id": _step_runtime_id(step),
            "runtime_session_id": step.get("runtime_session_id"),
            "artifact_summaries": step.get("artifacts") or [],
            "output_excerpt": step.get("output_excerpt"),
            "label": step.get("title"),
            "current_url": None,
            "is_read_only": step.get("type") in {"inspect", "verify"},
        }
        for step in steps
    ]
    active_step = next((step for step in steps if str(step.get("status") or "") in {"running", "pending_approval", "failed", "queued"}), None)
    trace["steps"] = serialized_steps
    trace["operator_plan_id"] = plan.id
    trace["operator_plan_status"] = plan.status
    trace["operator_stage"] = plan.operator_stage
    trace["active_step_id"] = _step_runtime_id(active_step) if active_step else None
    trace["pending_approval_count"] = plan.pending_approval_count
    trace["latest_artifact_summaries"] = list(plan.artifacts_json or [])
    trace["artifact_summaries"] = list(plan.artifacts_json or [])
    trace["child_execution_ids"] = list(plan.child_execution_ids_json or [])
    trace["runtime_execution_ids"] = list(plan.child_execution_ids_json or [])
    trace["step_verification_summary"] = next((str(step.get("verification_summary")) for step in reversed(steps) if step.get("verification_summary")), trace.get("step_verification_summary"))
    return inject_operator_plan_trace_fields(trace, plan)


async def _persist_plan(session: AsyncSession, plan: OperatorPlan, *, base_trace: dict[str, Any] | None = None) -> OperatorPlan:
    plan.trace_json = _build_trace_from_plan(plan, base_trace=base_trace)
    await session.commit()
    await session.refresh(plan)
    return plan


def _apply_trace_to_step(step: dict[str, Any], trace: dict[str, Any], *, parent_execution_id: str, child_execution_id: str | None = None) -> None:
    step["parent_execution_id"] = parent_execution_id
    if child_execution_id:
      step["child_execution_id"] = child_execution_id
    step["requested_actions"] = list(trace.get("requested_desktop_actions") or [])
    step["artifacts"] = list(trace.get("artifact_summaries") or trace.get("desktop_artifacts") or [])
    step["summary"] = str((trace.get("trace_summary") or {}).get("summary") or trace.get("failure_summary") or step.get("title"))
    step["output_excerpt"] = str(trace.get("step_verification_summary") or trace.get("failure_summary") or step["summary"])
    step["verification_summary"] = str(trace.get("step_verification_summary") or (trace.get("trace_summary") or {}).get("summary") or step["summary"])
    if isinstance(trace.get("desktop_action_approval"), dict):
        step["approval"] = trace["desktop_action_approval"]


def _aggregate_plan_state(plan: OperatorPlan) -> None:
    steps = list(plan.steps_json or [])
    plan.pending_approval_count = sum(1 for step in steps if str(step.get("status") or "") == "pending_approval")
    child_ids: list[str] = []
    artifacts: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []
    last_failure = None
    for step in steps:
        for key in ("parent_execution_id", "child_execution_id"):
            value = str(step.get(key) or "").strip()
            if value and value not in child_ids:
                child_ids.append(value)
        approval = step.get("approval")
        if isinstance(approval, dict):
            approvals.append(approval)
        for artifact in step.get("artifacts") or []:
            if isinstance(artifact, dict):
                artifacts.append(artifact)
        if step.get("status") == "failed" and step.get("output_excerpt"):
            last_failure = str(step["output_excerpt"])
    plan.child_execution_ids_json = child_ids
    plan.artifacts_json = artifacts
    plan.approvals_json = approvals
    plan.last_failure_summary = last_failure


async def _create_step_execution(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    plan: OperatorPlan,
    step: dict[str, Any],
) -> RuntimeExecution:
    return await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="operator",
        execution_kind=f"operator_plan_{step['type']}",
        provider_id=conversation.provider_id if conversation else None,
        model_id=conversation.model_id if conversation else None,
        provider_connection_id=conversation.provider_connection_id if conversation else None,
        resolved_model_name=conversation.model_name if conversation else None,
        resolved_base_url=conversation.provider_connection.base_url if conversation and conversation.provider_connection else None,
        conversation_id=conversation.id if conversation else None,
        prompt_preview=str(step["prompt"])[:400],
        details_json={"operator_plan_id": plan.id, "operator_step_id": step["id"], "mode": step["mode"]},
    )


async def _run_trace_step(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    plan: OperatorPlan,
    step: dict[str, Any],
    prompt_override: str | None = None,
) -> tuple[RuntimeExecution, dict[str, Any]]:
    execution = await _create_step_execution(session, workspace=workspace, user=user, conversation=conversation, plan=plan, step=step)
    await mark_runtime_running(session, execution)
    try:
        trace = await collect_desktop_operator_trace(
            session,
            workspace=workspace,
            user=user,
            conversation=conversation,
            parent_execution=execution,
            prompt=prompt_override or str(step["prompt"]),
            mode=str(step["mode"]),
        )
        await mark_runtime_succeeded(
            session,
            execution,
            response_preview=str((trace.get("trace_summary") or {}).get("summary") or step["title"])[:400],
            details_json={"execution_trace": trace, "operator_plan_id": plan.id, "operator_step_id": step["id"], "mode": step["mode"]},
            artifacts_json=trace.get("artifact_summaries"),
        )
        return execution, trace
    except Exception as exc:
        await mark_runtime_failed(
            session,
            execution,
            error_message=str(exc),
            details_json={"operator_plan_id": plan.id, "operator_step_id": step["id"], "mode": step["mode"]},
        )
        raise


async def execute_operator_plan(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    plan: OperatorPlan,
    start_index: int = 0,
) -> OperatorPlan:
    steps = list(plan.steps_json or [])
    for index in range(start_index, len(steps)):
        step = steps[index]
        status = str(step.get("status") or "pending")
        if status == "completed":
            continue
        if status == "denied":
            plan.status = "blocked"
            plan.operator_stage = "complete"
            plan.steps_json = steps
            _aggregate_plan_state(plan)
            return await _persist_plan(session, plan)

        plan.status = "running"
        plan.operator_stage = "approval" if step.get("type") in {"operate", "proposal"} else "execution"
        step["status"] = "running"
        plan.steps_json = steps
        _aggregate_plan_state(plan)
        await _persist_plan(session, plan)

        execution, trace = await _run_trace_step(session, workspace=workspace, user=user, conversation=conversation, plan=plan, step=step)
        _apply_trace_to_step(step, trace, parent_execution_id=execution.id)

        if step.get("type") in {"operate", "proposal"}:
            step["status"] = "pending_approval"
            step["summary"] = str((trace.get("desktop_action_approval") or {}).get("summary") or step["summary"])
            plan.status = "pending_approval"
            plan.operator_stage = "approval"
            plan.parent_execution_id = execution.id
            plan.steps_json = steps
            _aggregate_plan_state(plan)
            return await _persist_plan(session, plan, base_trace=trace)

        if trace.get("failure_summary") and int(step.get("retry_count") or 0) < MAX_STEP_RETRIES:
            retry_prompt = f"{step['prompt']} Narrow the follow-up to {(trace.get('primary_failure_target') or (trace.get('primary_grounded_target') or {}).get('value') or 'the grounded target')} and retry once."
            step["retry_count"] = int(step.get("retry_count") or 0) + 1
            step["reflection_summary"] = str((trace.get("reflection_summary") or {}).get("summary") or "Retrying once with a narrower grounded follow-up.")
            retry_execution, retry_trace = await _run_trace_step(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                plan=plan,
                step=step,
                prompt_override=retry_prompt,
            )
            _apply_trace_to_step(step, retry_trace, parent_execution_id=retry_execution.id)
            trace = retry_trace
            execution = retry_execution

        if trace.get("failure_summary"):
            step["status"] = "failed"
            plan.status = "failed"
            plan.operator_stage = "reflection" if step.get("reflection_summary") else "complete"
            plan.parent_execution_id = execution.id
            plan.steps_json = steps
            _aggregate_plan_state(plan)
            return await _persist_plan(session, plan, base_trace=trace)

        step["status"] = "completed"
        plan.parent_execution_id = execution.id
        plan.steps_json = steps
        _aggregate_plan_state(plan)
        await _persist_plan(session, plan, base_trace=trace)

    plan.status = "completed"
    plan.operator_stage = "complete"
    plan.steps_json = steps
    _aggregate_plan_state(plan)
    return await _persist_plan(session, plan)


async def create_and_execute_operator_plan(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    title: str,
    prompt: str,
    mode: str,
    template_slug: str | None = None,
) -> OperatorPlan:
    plan = OperatorPlan(
        id=generate_entity_id("oplan"),
        workspace_id=workspace.id,
        conversation_id=conversation.id if conversation else None,
        created_by_id=user.id,
        title=title,
        mode=mode,
        status="queued",
        operator_stage="grounding",
        requested_prompt=prompt,
        template_slug=template_slug,
        steps_json=build_operator_plan_steps(prompt=prompt, mode=mode, template_slug=template_slug),
        approvals_json=[],
        artifacts_json=[],
        child_execution_ids_json=[],
        trace_json={},
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return await execute_operator_plan(session, workspace=workspace, user=user, conversation=conversation, plan=plan)


async def review_operator_plan(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    plan: OperatorPlan,
    decision: str,
) -> OperatorPlan:
    steps = list(plan.steps_json or [])
    current_index = next((index for index, item in enumerate(steps) if str(item.get("status") or "") == "pending_approval"), None)
    if current_index is None:
        raise ValueError("This operator plan does not have a pending approval step.")
    step = steps[current_index]
    parent_execution_id = str(step.get("parent_execution_id") or plan.parent_execution_id or "").strip()
    if not parent_execution_id:
        raise ValueError("Pending approval step is missing its parent execution.")
    parent_execution = await session.get(RuntimeExecution, parent_execution_id)
    if not parent_execution:
        raise ValueError("Parent runtime execution not found for the pending approval step.")

    updated_parent, child_execution, trace = await review_desktop_action_approval(
        session,
        workspace=workspace,
        user=user,
        parent_execution=parent_execution,
        decision=decision,
    )
    _apply_trace_to_step(step, trace, parent_execution_id=updated_parent.id, child_execution_id=child_execution.id if child_execution else None)
    step["status"] = "denied" if decision == "denied" else "completed"
    step["verification_summary"] = str(trace.get("step_verification_summary") or (trace.get("desktop_action_approval") or {}).get("summary") or step.get("summary"))
    plan.parent_execution_id = updated_parent.id
    plan.steps_json = steps
    _aggregate_plan_state(plan)

    if decision == "denied":
        plan.status = "blocked"
        plan.operator_stage = "complete"
        return await _persist_plan(session, plan, base_trace=trace)

    plan.status = "running"
    plan.operator_stage = "execution"
    await _persist_plan(session, plan, base_trace=trace)
    return await execute_operator_plan(session, workspace=workspace, user=user, conversation=conversation, plan=plan, start_index=current_index + 1)


async def resume_operator_plan_execution(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation | None,
    plan: OperatorPlan,
) -> OperatorPlan:
    steps = list(plan.steps_json or [])
    current_index = next((index for index, item in enumerate(steps) if str(item.get("status") or "") not in {"completed"}), None)
    if current_index is None:
        plan.status = "completed"
        plan.operator_stage = "complete"
        return await _persist_plan(session, plan)
    if str(steps[current_index].get("status") or "") == "denied":
        steps[current_index]["status"] = "pending"
        steps[current_index].pop("approval", None)
        steps[current_index].pop("parent_execution_id", None)
        steps[current_index].pop("child_execution_id", None)
        plan.steps_json = steps
        _aggregate_plan_state(plan)
        await _persist_plan(session, plan)
    return await execute_operator_plan(session, workspace=workspace, user=user, conversation=conversation, plan=plan, start_index=current_index)
