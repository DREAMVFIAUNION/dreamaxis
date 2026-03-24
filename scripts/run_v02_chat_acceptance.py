from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

API_BASE = os.environ.get("DREAMAXIS_API_BASE_URL", "http://127.0.0.1:8000")
REPO_ROOT_HOST = Path(r"D:\DreamAxis\dreamaxis")
REPO_ROOT_CONTAINER = PurePosixPath("/workspace")
VALIDATION_WORKSPACES_HOST = REPO_ROOT_HOST / "artifacts" / "validation-workspaces"
VALIDATION_WORKSPACES_CONTAINER = REPO_ROOT_CONTAINER / "artifacts" / "validation-workspaces"
REPORT_PATH = Path(r"D:\DreamAxis\dreamaxis\docs\chat-acceptance-report-v0.2.md")
REPORT_JSON_PATH = Path(r"D:\DreamAxis\dreamaxis\artifacts\acceptance\chat-v0.2-results.json")


@dataclass
class Scenario:
    repo_label: str
    workspace_label: str
    workspace_slug: str
    workspace_root: str
    scenario: str
    mode: str
    prompt: str
    expect_browser: bool = False
    expect_proposal: bool = False


class Runner:
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=API_BASE, timeout=240)
        self.token = ""
        self.connection: dict[str, Any] | None = None
        self.provider_test: dict[str, Any] | None = None
        self.workspaces: dict[str, str] = {}
        self.results: list[dict[str, Any]] = []

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def bootstrap(self) -> None:
        last_error: Exception | None = None
        for _ in range(10):
            try:
                payload = self.client.post("/api/v1/auth/bootstrap")
                payload.raise_for_status()
                data = payload.json()
                self.token = data["data"]["access_token"]
                return
            except (httpx.HTTPError, httpx.RemoteProtocolError, KeyError) as exc:
                last_error = exc
                time.sleep(1)
        raise RuntimeError("Failed to bootstrap local auth session for acceptance run.") from last_error

    def ensure_connection(self) -> None:
        items = self.client.get("/api/v1/provider-connections", headers=self.headers).json()["data"]
        connection = next((item for item in items if item["name"] == "NVIDIA Build"), None)
        if not connection:
            raise SystemExit("NVIDIA Build provider connection not found. Recreate it locally before running v0.2 acceptance.")
        self.connection = connection
        self.provider_test = self.client.post(f"/api/v1/provider-connections/{connection['id']}/test", headers=self.headers).json()["data"]

    def ensure_workspace(self, label: str, slug: str, root_path: str) -> str:
        if label in self.workspaces:
            return self.workspaces[label]
        items = self.client.get("/api/v1/workspaces", headers=self.headers).json()["data"]
        normalized_root = root_path.replace("\\", "/")
        match = next((item for item in items if item["slug"] == slug and str(item.get("workspace_root_path") or "").replace("\\", "/") == normalized_root), None)
        if match:
            self.workspaces[label] = match["id"]
            return match["id"]
        payload = {
            "name": label,
            "slug": slug,
            "description": f"v0.2 acceptance workspace for {label}",
            "workspace_root_path": normalized_root,
            "default_provider_connection_id": self.connection["id"],
            "default_model_name": self.connection.get("default_model_name") or "qwen/qwen3-coder-480b-a35b-instruct",
            "default_embedding_model_name": self.connection.get("default_embedding_model_name"),
        }
        workspace = self.client.post("/api/v1/workspaces", headers=self.headers, json=payload).json()["data"]
        self.workspaces[label] = workspace["id"]
        return workspace["id"]

    def create_conversation(self, workspace_id: str, title: str) -> str:
        payload = {
            "workspace_id": workspace_id,
            "title": title,
            "provider_connection_id": self.connection["id"],
            "model_name": self.connection.get("default_model_name") or "qwen/qwen3-coder-480b-a35b-instruct",
            "use_knowledge": True,
        }
        return self.client.post("/api/v1/conversations", headers=self.headers, json=payload).json()["data"]["id"]

    def stream_prompt(self, conversation_id: str, prompt: str, mode: str) -> list[dict[str, Any]]:
        payload = {"conversation_id": conversation_id, "content": prompt, "use_knowledge": True, "mode": mode}
        events: list[dict[str, Any]] = []
        with self.client.stream("POST", "/api/v1/messages/stream", headers=self.headers, json=payload) as response:
            response.raise_for_status()
            event_name: str | None = None
            data_lines: list[str] = []
            for raw_line in response.iter_lines():
                if raw_line is None:
                    continue
                line = raw_line.strip()
                if not line:
                    if event_name:
                        data = json.loads("\n".join(data_lines)) if data_lines else {}
                        events.append({"event": event_name, "data": data})
                    event_name = None
                    data_lines = []
                    continue
                if line.startswith("event:"):
                    event_name = line.removeprefix("event:").strip()
                elif line.startswith("data:"):
                    data_lines.append(line.removeprefix("data:").strip())
        return events

    def validate(self, scenario: Scenario, workspace_id: str, conversation_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        names = [event["event"] for event in events]
        start = next((event["data"] for event in events if event["event"] == "message_start"), {})
        finish = next((event["data"] for event in events if event["event"] == "finish"), {})
        trace = finish.get("execution_trace") or start.get("execution_trace") or {}
        content = str(finish.get("content") or "")
        parent_execution_id = finish.get("runtime_execution_id") or start.get("runtime_execution_id")
        runtime_execution_ids = finish.get("runtime_execution_ids") or start.get("runtime_execution_ids") or []
        proposal = finish.get("proposal") or start.get("proposal") or trace.get("proposal")
        notes: list[str] = []
        failed_steps = [step for step in steps if step.get("status") == "failed"] if (steps := trace.get("steps") or []) else []

        mode_ok = str(trace.get("mode") or finish.get("mode") or start.get("mode") or "") == scenario.mode
        if not mode_ok:
            notes.append(f"expected mode={scenario.mode}, got {trace.get('mode') or finish.get('mode') or start.get('mode')}")

        sse_ok = names[:1] == ["message_start"] and "finish" in names and names[-1:] == ["done"]
        if not sse_ok:
            notes.append(f"unexpected SSE sequence: {names}")

        sections_ok = all(section in content for section in ["## Intent / plan", "## What ran", "## What was found", "## Recommended next step"])
        if not sections_ok:
            notes.append("missing one or more required headings")

        trace_ok = bool(trace and trace.get("execution_bundle_id") and trace.get("runtime_execution_ids") is not None and (trace.get("evidence_items") or trace.get("evidence")))
        if not trace_ok:
            notes.append("trace missing execution bundle or evidence")

        evidence_ok = bool(trace.get("evidence_items") or trace.get("evidence"))
        if not evidence_ok:
            notes.append("no evidence items returned")

        grounding_summary = trace.get("grounding_summary") or {}
        grounded_targets = trace.get("grounded_targets") or []
        primary_grounded_target = trace.get("primary_grounded_target") or {}
        grounding_ok = bool(
            grounding_summary.get("summary")
            and grounded_targets
            and primary_grounded_target.get("value")
        )
        if not grounding_ok:
            notes.append("trace missing grounding summary / grounded targets")

        proposal_ok = True
        if scenario.expect_proposal:
            proposal_ok = bool(proposal and proposal.get("not_applied") is True and proposal.get("targets"))
            if not proposal_ok:
                notes.append("proposal mode did not return a grounded proposal-only payload")
        elif proposal:
            notes.append("proposal payload appeared on a non-proposal scenario")

        browser_ok = True
        if scenario.expect_browser:
            browser_ok = any(step.get("kind") == "browser" and step.get("status") in {"succeeded", "failed"} for step in steps)
            if not browser_ok:
                notes.append("verify scenario did not invoke browser runtime")

        troubleshooting_ok = True
        failure_target_ok = True
        reflection_ok = True
        reflection_summary = trace.get("reflection_summary") or {}
        if failed_steps:
            failure_summary = trace.get("failure_summary")
            failure_classification = trace.get("failure_classification")
            primary_failure_target = trace.get("primary_failure_target")
            stderr_highlights = trace.get("stderr_highlights") or []
            grounded_reasoning = trace.get("grounded_next_step_reasoning") or []
            troubleshooting_ok = bool(
                failure_summary
                and failure_classification
                and stderr_highlights
                and grounded_reasoning
            )
            failure_target_ok = bool(primary_failure_target)
            if not failure_summary:
                notes.append("failed trace missing failure_summary")
            if not failure_classification:
                notes.append("failed trace missing failure_classification")
            if not primary_failure_target:
                notes.append("failed trace missing primary_failure_target")
            if not stderr_highlights:
                notes.append("failed trace missing stderr_highlights")
            if not grounded_reasoning:
                notes.append("failed trace missing grounded_next_step_reasoning")
            reflection_ok = bool(
                reflection_summary
                and trace.get("reflection_summary")
                and trace.get("reflection_reason")
                and (not reflection_summary.get("triggered") or trace.get("reflection_next_probe"))
            )
            if not reflection_ok:
                notes.append("failed trace missing reflection summary / follow-up metadata")
        elif reflection_summary.get("triggered"):
            reflection_ok = bool(trace.get("reflection_reason") and trace.get("reflection_next_probe"))
            if not reflection_ok:
                notes.append("triggered reflection missing reason / next probe")

        runtime_link_ok = True
        parent_payload: dict[str, Any] | None = None
        if parent_execution_id:
            parent_payload = self.client.get(f"/api/v1/runtime-executions/{parent_execution_id}", headers=self.headers).json()["data"]
            runtime_link_ok = (
                parent_payload.get("execution_bundle_id") == parent_execution_id
                and str(parent_payload.get("mode") or "") == scenario.mode
                and sorted(parent_payload.get("child_execution_ids") or []) == sorted(runtime_execution_ids)
            )
            if not runtime_link_ok:
                notes.append("parent execution linkage metadata was incomplete")
            for child_id in runtime_execution_ids:
                child = self.client.get(f"/api/v1/runtime-executions/{child_id}", headers=self.headers).json()["data"]
                if child.get("parent_execution_id") != parent_execution_id:
                    runtime_link_ok = False
                    notes.append(f"child execution {child_id} missing parent link")
                    break
        else:
            runtime_link_ok = False
            notes.append("missing parent runtime execution id")

        safety = trace.get("safety_summary") or {}
        safety_ok = bool(safety.get("blocked_write_actions") is True)
        if scenario.expect_proposal:
            safety_ok = safety_ok and bool(safety.get("proposal_only") is True)
        if not safety_ok:
            notes.append("safety summary did not confirm blocked writes / proposal-only mode")

        overall_ok = all(
            [
                mode_ok,
                sse_ok,
                sections_ok,
                trace_ok,
                evidence_ok,
                grounding_ok,
                proposal_ok,
                browser_ok,
                troubleshooting_ok,
                failure_target_ok,
                reflection_ok,
                runtime_link_ok,
                safety_ok,
            ]
        )
        return {
            "repo": scenario.repo_label,
            "workspace_label": scenario.workspace_label,
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "scenario": scenario.scenario,
            "mode": scenario.mode,
            "prompt": scenario.prompt,
            "ok": overall_ok,
            "mode_ok": mode_ok,
            "sse_ok": sse_ok,
            "sections_ok": sections_ok,
            "trace_ok": trace_ok,
            "evidence_ok": evidence_ok,
            "grounding_ok": grounding_ok,
            "proposal_ok": proposal_ok,
            "browser_ok": browser_ok,
            "troubleshooting_ok": troubleshooting_ok,
            "failure_target_ok": failure_target_ok,
            "reflection_ok": reflection_ok,
            "runtime_link_ok": runtime_link_ok,
            "safety_ok": safety_ok,
            "notes": notes,
            "parent_execution_id": parent_execution_id,
            "child_execution_ids": runtime_execution_ids,
            "trace_summary": trace.get("trace_summary"),
            "grounding_summary": grounding_summary,
            "primary_grounded_target": primary_grounded_target,
            "reflection_summary": reflection_summary,
            "proposal": proposal,
            "parent_execution": parent_payload,
        }

    def write_report(self) -> None:
        passed = [item for item in self.results if item["ok"]]
        failed = [item for item in self.results if not item["ok"]]
        lines = [
            "# DreamAxis v0.2 Chat-first Acceptance Report",
            "",
            "## Validation baseline",
            "",
            f"- Provider connection: `{self.connection['name']}`",
            f"- Provider status: `{self.connection['status']}`",
            f"- Test status: `{(self.provider_test or {}).get('status', '--')}`",
            f"- Test message: {(self.provider_test or {}).get('message', '--')}",
            f"- Chat model: `{self.connection.get('default_model_name') or '--'}`",
            f"- Embedding model: `{self.connection.get('default_embedding_model_name') or '--'}`",
            f"- API base: `{API_BASE}`",
            "",
            "## Scenario matrix",
            "",
            "| Repo | Scenario | Mode | Result | Mode | Trace | Evidence | Grounding | Proposal | Browser | Troubleshooting | Failure target | Reflection | Runtime linkage | Safety | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in self.results:
            notes = "<br>".join(item["notes"]) if item["notes"] else "ok"
            lines.append(
                f"| {item['repo']} | {item['scenario']} | `{item['mode']}` | {'PASS' if item['ok'] else 'FAIL'} | "
                f"{'ok' if item['mode_ok'] else 'fail'} | {'ok' if item['trace_ok'] else 'fail'} | {'ok' if item['evidence_ok'] else 'fail'} | {'ok' if item['grounding_ok'] else 'fail'} | "
                f"{'ok' if item['proposal_ok'] else 'fail'} | {'ok' if item['browser_ok'] else 'fail'} | {'ok' if item['troubleshooting_ok'] else 'fail'} | {'ok' if item['failure_target_ok'] else 'fail'} | {'ok' if item['reflection_ok'] else 'fail'} | {'ok' if item['runtime_link_ok'] else 'fail'} | {'ok' if item['safety_ok'] else 'fail'} | {notes} |"
            )
        lines.extend([
            "",
            "## Screenshot anchors",
            "",
        ])
        for item in self.results:
            if item["repo"] == "DreamAxis" and item["scenario"] in {"verify-dashboard", "propose-fix-chat"}:
                lines.append(f"- `{item['scenario']}` conversation: `/chat/{item['conversation_id']}`")
        lines.extend([
            "",
            "## Summary",
            "",
            f"- Passed: `{len(passed)}`",
            f"- Failed: `{len(failed)}`",
            "",
            "## Next fixes",
            "",
        ])
        if failed:
            for item in failed:
                lines.append(f"- {item['repo']} / {item['scenario']}: {'; '.join(item['notes'])}")
        else:
            lines.append("- v0.2 grounded verify loop is passing with visible grounding targets, reflection-aware follow-up probes, proposal-only edits, and runtime-linked evidence across the acceptance set.")
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON_PATH.write_text(json.dumps(self.results, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self) -> None:
        self.bootstrap()
        self.ensure_connection()
        scenarios = [
            Scenario("DreamAxis", "DreamAxis v0.2", "dreamaxis-v02-acceptance", REPO_ROOT_CONTAINER.as_posix(), "understand-onboarding", "understand_repo", "What is this repo and how do I start it?"),
            Scenario("DreamAxis", "DreamAxis v0.2", "dreamaxis-v02-acceptance", REPO_ROOT_CONTAINER.as_posix(), "inspect-provider-settings", "inspect_repo", "Trace the provider settings flow."),
            Scenario("DreamAxis", "DreamAxis v0.2", "dreamaxis-v02-acceptance", REPO_ROOT_CONTAINER.as_posix(), "verify-dashboard", "verify_repo", "Verify /dashboard and capture the result.", expect_browser=True),
            Scenario("DreamAxis", "DreamAxis v0.2", "dreamaxis-v02-acceptance", REPO_ROOT_CONTAINER.as_posix(), "propose-fix-chat", "propose_fix", "Propose a safe fix path for the v0.2 chat verification lane without changing files.", expect_proposal=True),
            Scenario("Paperclip", "Paperclip v0.2", "paperclip-v02-acceptance", (VALIDATION_WORKSPACES_CONTAINER / "paperclip").as_posix(), "verify-readiness", "verify_repo", "Is this workspace ready to run locally and what should I verify first?"),
            Scenario("Paperclip", "Paperclip v0.2", "paperclip-v02-acceptance", (VALIDATION_WORKSPACES_CONTAINER / "paperclip").as_posix(), "inspect-entrypoint", "inspect_repo", "Trace the main workspace entrypoint."),
            Scenario("Brain Core", "Brain Core v0.2", "brain-core-v02-acceptance", (VALIDATION_WORKSPACES_CONTAINER / "brain-core").as_posix(), "verify-readiness", "verify_repo", "Is this Python workspace ready to run locally?"),
            Scenario("Brain Core", "Brain Core v0.2", "brain-core-v02-acceptance", (VALIDATION_WORKSPACES_CONTAINER / "brain-core").as_posix(), "propose-fix-startup", "propose_fix", "Propose a safe troubleshooting path for this Python service without changing files.", expect_proposal=True),
        ]
        for scenario in scenarios:
            workspace_id = self.ensure_workspace(scenario.workspace_label, scenario.workspace_slug, scenario.workspace_root)
            conversation_id = self.create_conversation(workspace_id, f"{scenario.repo_label} / {scenario.scenario}")
            events = self.stream_prompt(conversation_id, scenario.prompt, scenario.mode)
            self.results.append(self.validate(scenario, workspace_id, conversation_id, events))
        self.write_report()


if __name__ == "__main__":
    runner = Runner()
    runner.run()
    print(f"Wrote {REPORT_PATH}")
