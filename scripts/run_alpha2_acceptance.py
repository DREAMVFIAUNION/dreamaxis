from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

API_BASE = os.environ.get("DREAMAXIS_API_BASE_URL", "http://127.0.0.1:8000")
REPORT_JSON_PATH = Path(r"D:\DreamAxis\dreamaxis\artifacts\acceptance\alpha2-results.json")


@dataclass
class OperatorScenario:
    key: str
    title: str
    workspace_id: str
    template_slug: str | None = None
    prompt: str | None = None
    mode: str | None = None
    approve_after_create: bool = False


@dataclass
class RepoScenario:
    key: str
    title: str
    workspace_id: str
    mode: str
    prompt: str


class AcceptanceRunner:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.token = ""
        self.user: dict[str, Any] = {}
        self.workspaces: dict[str, dict[str, Any]] = {}
        self.runtimes: list[dict[str, Any]] = []
        self.provider_connections: list[dict[str, Any]] = []
        self.results: dict[str, Any] = {
            "meta": {
                "api_base": API_BASE,
                "ran_at": None,
                "user": None,
            },
            "preflight": {},
            "operator_scenarios": [],
            "repo_scenarios": [],
            "ui_targets": {},
            "summary": {},
        }

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _url(self, path: str) -> str:
        return f"{API_BASE}{path}"

    def bootstrap(self) -> None:
        response = self.session.post(self._url("/api/v1/auth/bootstrap"), timeout=60)
        response.raise_for_status()
        payload = response.json()["data"]
        self.token = payload["access_token"]
        self.user = payload["user"]
        self.results["meta"]["user"] = self.user

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        response = self.session.get(self._url(path), headers=self.headers, params=params, timeout=120)
        response.raise_for_status()
        return response.json()["data"]

    def post_json(self, path: str, *, payload: dict[str, Any] | None = None, timeout: int = 300) -> Any:
        response = self.session.post(self._url(path), headers=self.headers, json=payload or {}, timeout=timeout)
        response.raise_for_status()
        return response.json()["data"]

    def load_environment(self) -> None:
        workspace_items = self.get_json("/api/v1/workspaces")
        self.workspaces = {item["id"]: item for item in workspace_items}
        self.runtimes = self.get_json("/api/v1/runtimes")
        self.provider_connections = self.get_json("/api/v1/provider-connections")

    def preflight(self) -> None:
        required_workspaces = ["workspace-main", "workspace-e8e98dd05c"]
        required_runtime_ids = ["runtime-cli-local", "runtime-browser-local", "runtime-cli-host-local", "runtime-desktop-local"]
        runtime_ids = {item["id"] for item in self.runtimes}
        runtime_index = {item["id"]: item for item in self.runtimes}
        workspace_runtime_map: dict[str, list[str]] = {}
        for runtime in self.runtimes:
            scope_type = runtime.get("scope_type")
            scope_ref_id = runtime.get("scope_ref_id")
            if scope_type == "workspace" and scope_ref_id:
                workspace_runtime_map.setdefault(scope_ref_id, []).append(runtime["id"])

        self.results["preflight"] = {
            "workspace_ids_present": {wid: wid in self.workspaces for wid in required_workspaces},
            "workspace_runtime_map": workspace_runtime_map,
            "runtime_ids_present": {rid: rid in runtime_ids for rid in required_runtime_ids},
            "runtime_status": {
                rid: {
                    "status": runtime_index[rid]["status"],
                    "doctor_status": runtime_index[rid].get("doctor_status"),
                    "scope_ref_id": runtime_index[rid].get("scope_ref_id"),
                }
                for rid in required_runtime_ids
                if rid in runtime_index
            },
        }

    def resolve_provider(self, workspace_id: str) -> tuple[str, str]:
        workspace = self.workspaces[workspace_id]
        provider_connection_id = workspace.get("default_provider_connection_id")
        model_name = workspace.get("default_model_name")
        if provider_connection_id and model_name:
            return provider_connection_id, model_name
        fallback = next((item for item in self.provider_connections if item.get("status") == "active"), None)
        if not fallback:
            raise RuntimeError(f"No active provider connection available for workspace {workspace_id}")
        fallback_model = (
            fallback.get("default_model_name")
            or self.workspaces["workspace-main"].get("default_model_name")
            or "gpt-4.1-mini"
        )
        return fallback["id"], fallback_model

    def create_conversation(self, workspace_id: str, title: str) -> dict[str, Any]:
        provider_connection_id, model_name = self.resolve_provider(workspace_id)
        payload = {
            "workspace_id": workspace_id,
            "title": title,
            "provider_connection_id": provider_connection_id,
            "model_name": model_name,
            "use_knowledge": True,
        }
        return self.post_json("/api/v1/conversations", payload=payload)

    def get_operator_plan(self, plan_id: str) -> dict[str, Any]:
        return self.get_json(f"/api/v1/operator-plans/{plan_id}")

    def wait_for_operator_plan(self, plan_id: str, *, timeout_s: int = 15) -> dict[str, Any]:
        deadline = time.time() + timeout_s
        last_payload = self.get_operator_plan(plan_id)
        while time.time() < deadline:
            status = str(last_payload.get("status") or "")
            if status not in {"queued", "running"}:
                return last_payload
            time.sleep(1)
            last_payload = self.get_operator_plan(plan_id)
        return last_payload

    def get_runtime_execution(self, execution_id: str | None) -> dict[str, Any] | None:
        if not execution_id:
            return None
        return self.get_json(f"/api/v1/runtime-executions/{execution_id}")

    def classify_operator_result(self, scenario: OperatorScenario, plan: dict[str, Any], *, created: dict[str, Any]) -> tuple[str, list[str]]:
        notes: list[str] = []
        steps = list(plan.get("steps_json") or [])
        trace = plan.get("trace_json") or {}
        artifacts = list(plan.get("artifacts_json") or [])
        verification_summary = trace.get("step_verification_summary") or plan.get("last_failure_summary")
        status = str(plan.get("status") or "")

        if scenario.approve_after_create:
            pre_status = str(created.get("status") or "")
            if pre_status != "pending_approval":
                notes.append(f"expected pre-approval pending_approval, got {pre_status}")
            if int(created.get("pending_approval_count") or 0) <= 0:
                notes.append("pre-approval pending_approval_count did not increment")
            if status != "completed":
                notes.append(f"expected approved plan to complete, got {status}")
        else:
            if status != "completed":
                notes.append(f"expected completed status, got {status}")

        if not verification_summary:
            notes.append("missing step verification summary or failure summary")
        if not plan.get("parent_execution_id"):
            notes.append("missing parent execution id")
        if not plan.get("child_execution_ids_json"):
            notes.append("missing child execution ids")
        if not artifacts:
            notes.append("no artifact summaries recorded")
        if scenario.key == "operate_with_approval":
            approvals = list(plan.get("approvals_json") or [])
            if not approvals:
                notes.append("approval history missing from plan")

        result = "pass" if not notes else "partial"
        if status in {"failed", "blocked"}:
            result = "fail"
        return result, notes

    def run_operator_scenario(self, scenario: OperatorScenario) -> dict[str, Any]:
        conversation = self.create_conversation(scenario.workspace_id, scenario.title)
        create_payload: dict[str, Any] = {
            "workspace_id": scenario.workspace_id,
            "conversation_id": conversation["id"],
            "title": scenario.title,
        }
        if scenario.template_slug:
            create_payload["template_slug"] = scenario.template_slug
        if scenario.prompt:
            create_payload["prompt"] = scenario.prompt
        if scenario.mode:
            create_payload["mode"] = scenario.mode

        created_plan = self.post_json("/api/v1/operator-plans", payload=create_payload, timeout=600)
        created_plan = self.wait_for_operator_plan(created_plan["id"])
        approval_transition: list[dict[str, Any]] = []
        final_plan = created_plan

        if scenario.approve_after_create:
            approval_transition.append(
                {
                    "phase": "before_approval",
                    "status": created_plan.get("status"),
                    "pending_approval_count": created_plan.get("pending_approval_count"),
                    "operator_stage": created_plan.get("operator_stage"),
                }
            )
            approved_plan = self.post_json(
                f"/api/v1/operator-plans/{created_plan['id']}/approve",
                payload={"decision": "approved"},
                timeout=600,
            )
            final_plan = self.wait_for_operator_plan(approved_plan["id"])
            approval_transition.append(
                {
                    "phase": "after_approval",
                    "status": final_plan.get("status"),
                    "pending_approval_count": final_plan.get("pending_approval_count"),
                    "operator_stage": final_plan.get("operator_stage"),
                }
            )

        parent_execution = self.get_runtime_execution(final_plan.get("parent_execution_id"))
        child_executions = [self.get_runtime_execution(item) for item in (final_plan.get("child_execution_ids_json") or [])]
        child_executions = [item for item in child_executions if item]
        result, notes = self.classify_operator_result(scenario, final_plan, created=created_plan)
        trace = final_plan.get("trace_json") or {}

        record = {
            "scenario_key": scenario.key,
            "scenario_title": scenario.title,
            "workspace_id": scenario.workspace_id,
            "workspace_name": self.workspaces[scenario.workspace_id]["name"],
            "conversation_id": conversation["id"],
            "conversation_title": conversation["title"],
            "operator_plan_id": final_plan["id"],
            "template_slug": scenario.template_slug,
            "prompt": scenario.prompt or final_plan.get("requested_prompt"),
            "mode": scenario.mode or final_plan.get("mode"),
            "result": result,
            "notes": notes,
            "status": final_plan.get("status"),
            "operator_stage": final_plan.get("operator_stage"),
            "approval_transition": approval_transition,
            "pending_approval_count": final_plan.get("pending_approval_count"),
            "parent_execution_id": final_plan.get("parent_execution_id"),
            "child_execution_ids": final_plan.get("child_execution_ids_json") or [],
            "artifacts": final_plan.get("artifacts_json") or [],
            "step_verification_summary": trace.get("step_verification_summary"),
            "last_failure_summary": final_plan.get("last_failure_summary"),
            "approvals": final_plan.get("approvals_json") or [],
            "steps": final_plan.get("steps_json") or [],
            "trace_summary": trace.get("trace_summary"),
            "runtime_trace": trace,
            "runtime_parent": parent_execution,
            "runtime_children": child_executions,
            "urls": {
                "chat": f"/chat/{conversation['id']}",
                "operator": f"/operator?plan={final_plan['id']}",
                "runtime": f"/runtime?execution={final_plan.get('parent_execution_id')}",
            },
        }
        return record

    def classify_repo_result(self, scenario: RepoScenario, response_data: dict[str, Any]) -> tuple[str, list[str]]:
        notes: list[str] = []
        trace = response_data.get("execution_trace") or {}
        runtime_execution_id = response_data.get("runtime_execution_id")
        assistant_content = ((response_data.get("assistant_message") or {}).get("content") or "").strip()
        proposal = response_data.get("proposal") or trace.get("proposal")
        if not runtime_execution_id:
            notes.append("missing runtime execution id")
        if not trace:
            notes.append("missing execution trace")
        if not assistant_content:
            notes.append("missing assistant content")
        if scenario.mode == "propose_fix":
            if not proposal:
                notes.append("missing proposal payload")
            elif proposal.get("not_applied") is not True:
                notes.append("proposal payload was not marked not_applied")
        elif scenario.key == "failure_reflection_narrowing":
            if not trace.get("failure_summary"):
                notes.append("missing failure summary")
            if not trace.get("primary_failure_target"):
                notes.append("missing primary failure target")
            if not trace.get("stderr_highlights"):
                notes.append("missing stderr highlights")
            if not trace.get("reflection_summary"):
                notes.append("missing reflection summary")
            elif not (trace.get("reflection_summary") or {}).get("summary"):
                notes.append("reflection summary did not include a summary")
        if scenario.mode in {"understand_repo", "inspect_repo", "verify_repo"} and proposal:
            notes.append("proposal payload unexpectedly present on non-proposal repo mode")
        result = "pass" if not notes else "partial"
        return result, notes

    def run_repo_scenario(self, scenario: RepoScenario) -> dict[str, Any]:
        conversation = self.create_conversation(scenario.workspace_id, scenario.title)
        response_data = self.post_json(
            "/api/v1/messages",
            payload={
                "conversation_id": conversation["id"],
                "content": scenario.prompt,
                "mode": scenario.mode,
                "use_knowledge": True,
            },
            timeout=600,
        )
        runtime_execution_id = response_data.get("runtime_execution_id")
        runtime_execution = self.get_runtime_execution(runtime_execution_id)
        trace = response_data.get("execution_trace") or {}
        result, notes = self.classify_repo_result(scenario, response_data)
        return {
            "scenario_key": scenario.key,
            "scenario_title": scenario.title,
            "workspace_id": scenario.workspace_id,
            "workspace_name": self.workspaces[scenario.workspace_id]["name"],
            "conversation_id": conversation["id"],
            "conversation_title": conversation["title"],
            "mode": scenario.mode,
            "prompt": scenario.prompt,
            "result": result,
            "notes": notes,
            "runtime_execution_id": runtime_execution_id,
            "runtime_execution_ids": response_data.get("runtime_execution_ids") or [],
            "proposal": response_data.get("proposal"),
            "assistant_message": response_data.get("assistant_message"),
            "trace": trace,
            "runtime_execution": runtime_execution,
            "urls": {
                "chat": f"/chat/{conversation['id']}",
                "runtime": f"/runtime?execution={runtime_execution_id}",
            },
        }

    def run(self) -> None:
        self.bootstrap()
        self.load_environment()
        self.preflight()
        self.results["meta"]["ran_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        operator_scenarios = [
            OperatorScenario(
                key="inspect_desktop",
                title="Alpha.2 acceptance — inspect active desktop",
                workspace_id="workspace-e8e98dd05c",
                template_slug="inspect-active-desktop",
            ),
            OperatorScenario(
                key="operate_with_approval",
                title="Alpha.2 acceptance — operate with approval",
                workspace_id="workspace-e8e98dd05c",
                prompt='Focus Chrome, press ctrl+l, and type "https://example.com".',
                mode="operate_desktop",
                approve_after_create=True,
            ),
            OperatorScenario(
                key="verify_browser",
                title="Alpha.2 acceptance — verify browser surface",
                workspace_id="workspace-e8e98dd05c",
                template_slug="verify-browser-surface",
            ),
            OperatorScenario(
                key="triad_summary",
                title="Alpha.2 acceptance — browser terminal vscode triad",
                workspace_id="workspace-e8e98dd05c",
                template_slug="browser-terminal-vscode-triad",
            ),
        ]
        repo_scenarios = [
            RepoScenario(
                key="failure_reflection_narrowing",
                title="Alpha.2 acceptance — failure reflection narrowing",
                workspace_id="workspace-main",
                mode="verify_repo",
                prompt="Verify http://127.0.0.1:3999/ and explain the failure with the next grounded probe.",
            ),
            RepoScenario(
                key="repo_understand",
                title="Alpha.2 acceptance — understand repo",
                workspace_id="workspace-main",
                mode="understand_repo",
                prompt="What is this repo and how do I start it?",
            ),
            RepoScenario(
                key="repo_inspect",
                title="Alpha.2 acceptance — inspect repo",
                workspace_id="workspace-main",
                mode="inspect_repo",
                prompt="Where is /operator implemented?",
            ),
            RepoScenario(
                key="repo_verify",
                title="Alpha.2 acceptance — verify repo readiness",
                workspace_id="workspace-main",
                mode="verify_repo",
                prompt="Verify the web app build path and local readiness.",
            ),
            RepoScenario(
                key="repo_propose_fix",
                title="Alpha.2 acceptance — propose safe fix",
                workspace_id="workspace-main",
                mode="propose_fix",
                prompt="Propose a safe fix path for the operator plan executor without changing files.",
            ),
        ]

        for scenario in operator_scenarios:
            self.results["operator_scenarios"].append(self.run_operator_scenario(scenario))

        for scenario in repo_scenarios:
            self.results["repo_scenarios"].append(self.run_repo_scenario(scenario))

        operator_records = self.results["operator_scenarios"]
        repo_records = self.results["repo_scenarios"]
        self.results["ui_targets"] = {
            "chat_urls": [item["urls"]["chat"] for item in operator_records + repo_records],
            "operator_urls": [item["urls"]["operator"] for item in operator_records],
            "runtime_urls": [item["urls"]["runtime"] for item in operator_records + repo_records if item["urls"].get("runtime")],
        }
        counts = {"pass": 0, "partial": 0, "fail": 0, "blocked": 0}
        for item in operator_records + repo_records:
            counts[item["result"]] = counts.get(item["result"], 0) + 1
        self.results["summary"] = {
            "counts": counts,
            "operator_passed": sum(1 for item in operator_records if item["result"] == "pass"),
            "operator_total": len(operator_records),
            "repo_passed": sum(1 for item in repo_records if item["result"] == "pass"),
            "repo_total": len(repo_records),
        }

    def write(self) -> None:
        REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON_PATH.write_text(json.dumps(self.results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    runner = AcceptanceRunner()
    runner.run()
    runner.write()
    print(f"Wrote {REPORT_JSON_PATH}")
