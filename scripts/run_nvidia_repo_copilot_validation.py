from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import httpx


REQUIRED_HEADINGS = [
    "## Intent / plan",
    "## What ran",
    "## What was found",
    "## Recommended next step",
]

REPO_ROOT_HOST = Path(r"D:\DreamAxis\dreamaxis")
REPO_ROOT_CONTAINER = PurePosixPath("/workspace")
VALIDATION_WORKSPACES_HOST = REPO_ROOT_HOST / "artifacts" / "validation-workspaces"
VALIDATION_WORKSPACES_CONTAINER = REPO_ROOT_CONTAINER / "artifacts" / "validation-workspaces"
SNAPSHOT_IGNORE = shutil.ignore_patterns(
    ".git",
    "node_modules",
    ".next",
    ".turbo",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
)


@dataclass
class ScenarioResult:
    repo_label: str
    scenario: str
    workspace_id: str
    conversation_id: str
    ok: bool
    provider_ok: bool
    sections_ok: bool
    trace_ok: bool
    runtime_ok: bool
    knowledge_ok: bool
    notes: list[str]
    runtime_execution_id: str | None = None
    runtime_execution_ids: list[str] | None = None
    model_name: str | None = None


class DreamAxisValidator:
    def __init__(self, *, base_url: str, api_key: str, chat_model: str, embedding_model: str, report_path: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.report_path = report_path
        self.client = httpx.Client(base_url=self.base_url, timeout=120)
        self.token: str | None = None
        self.provider_connection_id: str | None = None
        self.provider_summary: dict[str, Any] = {}
        self.workspace_index: dict[str, str] = {}
        self.results: list[ScenarioResult] = []
        self.knowledge_doc_status: dict[str, Any] | None = None

    def bootstrap(self) -> None:
        payload = self.client.post("/api/v1/auth/bootstrap").json()
        self.token = payload["data"]["access_token"]

    @property
    def headers(self) -> dict[str, str]:
        if not self.token:
            raise RuntimeError("Bootstrap token missing")
        return {"Authorization": f"Bearer {self.token}"}

    def get_or_create_nvidia_connection(self) -> None:
        existing = self.client.get("/api/v1/provider-connections", headers=self.headers).json()["data"]
        connection = next((item for item in existing if item["name"] == "NVIDIA Build"), None)
        body = {
            "provider_type": "openai_compatible",
            "name": "NVIDIA Build",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key": self.api_key,
            "model_discovery_mode": "auto",
            "default_model_name": self.chat_model,
            "default_embedding_model_name": self.embedding_model,
            "manual_models": [
                {"name": self.chat_model, "kind": "chat", "source": "manual"},
                {"name": self.embedding_model, "kind": "embedding", "source": "manual"},
            ],
        }
        if connection:
            response = self.client.patch(f"/api/v1/provider-connections/{connection['id']}", headers=self.headers, json=body).json()
            connection = response["data"]
        else:
            response = self.client.post("/api/v1/provider-connections", headers=self.headers, json=body).json()
            connection = response["data"]
        self.provider_connection_id = connection["id"]

        test_result = self.client.post(
            f"/api/v1/provider-connections/{self.provider_connection_id}/test",
            headers=self.headers,
        ).json()["data"]
        sync_result = self.client.post(
            f"/api/v1/provider-connections/{self.provider_connection_id}/sync-models",
            headers=self.headers,
        ).json()["data"]
        models = self.client.get(
            f"/api/v1/provider-connections/{self.provider_connection_id}/models",
            headers=self.headers,
        ).json()["data"]
        self.provider_summary = {
            "connection_id": self.provider_connection_id,
            "test": test_result,
            "sync": {
                "count": sync_result.get("count"),
                "warning": sync_result.get("warning"),
                "status": sync_result["connection"]["status"],
            },
            "model_names": [item["name"] for item in models[:20]],
        }

    def ensure_workspace(self, *, label: str, slug: str, root_path: str) -> str:
        if label in self.workspace_index:
            return self.workspace_index[label]

        items = self.client.get("/api/v1/workspaces", headers=self.headers).json()["data"]
        normalized_root_path = root_path.replace("\\", "/")
        requested = {
            "workspace_root_path": normalized_root_path,
            "default_provider_connection_id": self.provider_connection_id,
            "default_model_name": self.chat_model,
            "default_embedding_model_name": self.embedding_model,
        }

        def matches(item: dict[str, Any]) -> bool:
            for key, value in requested.items():
                current = item.get(key)
                if key == "workspace_root_path" and isinstance(current, str):
                    current = current.replace("\\", "/")
                if current != value:
                    return False
            return True

        existing = next((item for item in items if item["slug"] == slug), None)
        if existing and matches(existing):
            workspace_id = existing["id"]
        else:
            effective_slug = slug
            effective_label = label
            if existing and not matches(existing):
                embedding_suffix = re.sub(r"[^a-z0-9]+", "-", self.embedding_model.split("/")[-1].lower()).strip("-")
                effective_slug = f"{slug}-{embedding_suffix[:24]}".rstrip("-")
                effective_label = f"{label} ({self.embedding_model.split('/')[-1]})"
                existing = next((item for item in items if item["slug"] == effective_slug), None)
                if existing and matches(existing):
                    workspace_id = existing["id"]
                    self.workspace_index[label] = workspace_id
                    return workspace_id

            payload = {
                "name": effective_label,
                "slug": effective_slug,
                "description": f"Validation workspace for {effective_label}",
                **requested,
            }
            workspace_id = self.client.post("/api/v1/workspaces", headers=self.headers, json=payload).json()["data"]["id"]
        self.workspace_index[label] = workspace_id
        return workspace_id

    def prepare_runtime_visible_workspace(self, *, source_root: str, snapshot_slug: str) -> str:
        source = Path(source_root)
        if not source.exists():
            raise FileNotFoundError(f"Validation source repo does not exist: {source_root}")

        VALIDATION_WORKSPACES_HOST.mkdir(parents=True, exist_ok=True)
        target_host = VALIDATION_WORKSPACES_HOST / snapshot_slug
        if target_host.exists():
            shutil.rmtree(target_host)
        shutil.copytree(source, target_host, ignore=SNAPSHOT_IGNORE)

        relative = target_host.relative_to(REPO_ROOT_HOST)
        container_path = REPO_ROOT_CONTAINER / relative
        return str(container_path).replace("\\", "/")

    def create_conversation(self, *, workspace_id: str, title: str) -> str:
        payload = {
            "workspace_id": workspace_id,
            "title": title,
            "provider_connection_id": self.provider_connection_id,
            "model_name": self.chat_model,
            "use_knowledge": True,
        }
        return self.client.post("/api/v1/conversations", headers=self.headers, json=payload).json()["data"]["id"]

    def upload_knowledge_probe(self, workspace_id: str) -> dict[str, Any]:
        temp_path = Path(os.environ.get("TEMP", ".")) / "dreamaxis-nvidia-validation-note.md"
        temp_path.write_text(
            "# NVIDIA validation note\n"
            "If model discovery fails, test the connection first, then keep the chat model manual and verify the embedding model separately.\n"
            "DreamAxis should show operator-facing status instead of raw provider secrets.\n",
            encoding="utf-8",
        )
        with temp_path.open("rb") as file_handle:
            response = self.client.post(
                "/api/v1/knowledge/upload",
                headers=self.headers,
                data={"workspace_id": workspace_id},
                files={"file": (temp_path.name, file_handle, "text/markdown")},
            )
        response.raise_for_status()
        response = response.json()["data"]
        self.knowledge_doc_status = response
        return response

    def stream_prompt(self, conversation_id: str, prompt: str) -> dict[str, Any]:
        payload = {"conversation_id": conversation_id, "content": prompt, "use_knowledge": True}
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
        return {"events": events}

    def evaluate_stream_result(self, *, repo_label: str, scenario: str, workspace_id: str, conversation_id: str, stream_result: dict[str, Any]) -> ScenarioResult:
        events = stream_result["events"]
        names = [item["event"] for item in events]
        start = next((item["data"] for item in events if item["event"] == "message_start"), {})
        finish = next((item["data"] for item in events if item["event"] == "finish"), {})
        content = str(finish.get("content") or "")
        execution_trace = finish.get("execution_trace") or start.get("execution_trace") or {}
        runtime_execution_id = finish.get("runtime_execution_id") or start.get("runtime_execution_id")
        runtime_execution_ids = finish.get("runtime_execution_ids") or start.get("runtime_execution_ids") or []
        notes: list[str] = []

        provider_ok = names[:1] == ["message_start"] and names[-1:] == ["done"] and "finish" in names and ("delta" in names or finish)
        if not provider_ok:
            notes.append(f"Unexpected SSE sequence: {names}")

        sections_ok = all(section in content for section in REQUIRED_HEADINGS)
        if not sections_ok:
            notes.append("Missing one or more required repo-copilot headings.")

        trace_ok = bool(execution_trace and execution_trace.get("runtime_execution_ids") is not None and execution_trace.get("timeline"))
        if not trace_ok:
            notes.append("Execution trace was missing timeline or runtime execution ids.")

        trace_steps = execution_trace.get("steps") or []
        actionable_steps = [step for step in trace_steps if step.get("kind") in {"cli", "browser"}]
        successful_actionable_step = any(step.get("status") == "succeeded" for step in actionable_steps)
        evidenced_actionable_step = any(
            step.get("status") in {"succeeded", "failed"} and (step.get("output_excerpt") or step.get("artifact_summaries"))
            for step in actionable_steps
        )
        runtime_ok = False
        if runtime_execution_id:
            runtime_payload = self.client.get(f"/api/v1/runtime-executions/{runtime_execution_id}", headers=self.headers).json()["data"]
            timeline_payload = self.client.get(
                f"/api/v1/runtime-executions/{runtime_execution_id}/timeline",
                headers=self.headers,
            ).json()["data"]
            runtime_ok = bool(
                runtime_payload.get("provider_connection_id") == self.provider_connection_id
                and runtime_payload.get("resolved_model_name") == self.chat_model
                and timeline_payload.get("timeline")
            )
            if scenario in {"repo-onboarding", "feature-trace", "verification-workflow", "knowledge-assisted-troubleshooting"}:
                if scenario == "knowledge-assisted-troubleshooting":
                    runtime_ok = runtime_ok and evidenced_actionable_step
                else:
                    runtime_ok = runtime_ok and successful_actionable_step
            if not runtime_ok:
                if scenario == "knowledge-assisted-troubleshooting" and actionable_steps and not evidenced_actionable_step:
                    notes.append("Troubleshooting probes ran, but they did not return actionable output or artifacts.")
                elif actionable_steps and not successful_actionable_step:
                    notes.append("Runtime probes were recorded, but none of the CLI/browser steps completed successfully.")
                else:
                    notes.append("Runtime execution did not persist provider/model/timeline as expected.")
        else:
            notes.append("No runtime_execution_id was returned from the stream.")

        knowledge_ok = True
        if scenario == "knowledge-assisted-troubleshooting":
            sources = finish.get("sources") or start.get("sources") or []
            knowledge_ok = bool(sources)
            if not knowledge_ok:
                notes.append("Knowledge troubleshooting scenario did not return sources.")

        ok = provider_ok and sections_ok and trace_ok and runtime_ok and knowledge_ok
        return ScenarioResult(
            repo_label=repo_label,
            scenario=scenario,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            ok=ok,
            provider_ok=provider_ok,
            sections_ok=sections_ok,
            trace_ok=trace_ok,
            runtime_ok=runtime_ok,
            knowledge_ok=knowledge_ok,
            notes=notes,
            runtime_execution_id=runtime_execution_id,
            runtime_execution_ids=runtime_execution_ids,
            model_name=self.chat_model,
        )

    def run(self) -> None:
        self.bootstrap()
        self.get_or_create_nvidia_connection()

        dreamaxis_workspace = self.ensure_workspace(
            label="DreamAxis NVIDIA Validation",
            slug="dreamaxis-nvidia-validation-container",
            root_path=REPO_ROOT_CONTAINER.as_posix(),
        )
        paperclip_runtime_root = self.prepare_runtime_visible_workspace(
            source_root=r"D:\paperclip",
            snapshot_slug="paperclip",
        )
        brain_core_runtime_root = self.prepare_runtime_visible_workspace(
            source_root=r"D:\DREAMVFIA Assistant\dreamhelper-v3\services\brain-core",
            snapshot_slug="brain-core",
        )
        node_workspace = self.ensure_workspace(
            label="Paperclip NVIDIA Validation",
            slug="paperclip-nvidia-validation-container",
            root_path=paperclip_runtime_root,
        )
        python_workspace = self.ensure_workspace(
            label="Brain Core NVIDIA Validation",
            slug="brain-core-nvidia-validation-container",
            root_path=brain_core_runtime_root,
        )

        self.upload_knowledge_probe(dreamaxis_workspace)

        scenarios = [
            ("DreamAxis", dreamaxis_workspace, "repo-onboarding", "What is this repo and how do I start it?"),
            ("DreamAxis", dreamaxis_workspace, "environment-readiness", "Is this workspace ready to run locally?"),
            ("DreamAxis", dreamaxis_workspace, "feature-trace", "Trace the provider settings flow."),
            ("DreamAxis", dreamaxis_workspace, "verification-workflow", "Verify /dashboard and run lint build."),
            (
                "DreamAxis",
                dreamaxis_workspace,
                "knowledge-assisted-troubleshooting",
                "Using the uploaded NVIDIA validation note, what should I check next if model discovery fails?",
            ),
            ("Paperclip", node_workspace, "repo-onboarding", "What is this repo and how do I start it?"),
            ("Paperclip", node_workspace, "environment-readiness", "Is this workspace ready to run locally?"),
            ("Brain Core", python_workspace, "repo-onboarding", "What is this repo and how do I start it?"),
            ("Brain Core", python_workspace, "environment-readiness", "Is this workspace ready to run locally?"),
        ]

        for repo_label, workspace_id, scenario, prompt in scenarios:
            conversation_id = self.create_conversation(workspace_id=workspace_id, title=f"{repo_label} / {scenario}")
            stream_result = self.stream_prompt(conversation_id, prompt)
            self.results.append(
                self.evaluate_stream_result(
                    repo_label=repo_label,
                    scenario=scenario,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    stream_result=stream_result,
                )
            )
            time.sleep(1)

        self.write_report()

    def write_report(self) -> None:
        passed = [item for item in self.results if item.ok]
        blocked = [item for item in self.results if not item.ok and not item.provider_ok]
        degraded = [item for item in self.results if not item.ok and item.provider_ok]
        lines = [
            "# DreamAxis NVIDIA Chat Acceptance Report",
            "",
            "## Provider validation",
            "",
            f"- Connection ID: `{self.provider_summary.get('connection_id', '--')}`",
            f"- Test status: `{(self.provider_summary.get('test') or {}).get('status', '--')}`",
            f"- Test message: {(self.provider_summary.get('test') or {}).get('message', '--')}",
            f"- Sync count: `{(self.provider_summary.get('sync') or {}).get('count', '--')}`",
            f"- Sync warning: {(self.provider_summary.get('sync') or {}).get('warning', 'none')}",
            f"- Chat model: `{self.chat_model}`",
            f"- Embedding model: `{self.embedding_model}`",
            "",
            "## Knowledge upload",
            "",
            f"- Upload status: `{(self.knowledge_doc_status or {}).get('status', '--')}`",
            f"- Chunk count: `{(self.knowledge_doc_status or {}).get('chunk_count', '--')}`",
            f"- Error message: {(self.knowledge_doc_status or {}).get('error_message', 'none')}",
            "",
            "## Scenario results",
            "",
            "| Repo | Scenario | Result | Provider | Sections | Trace | Runtime | Knowledge | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in self.results:
            notes = "<br>".join(item.notes) if item.notes else "ok"
            lines.append(
                f"| {item.repo_label} | {item.scenario} | {'PASS' if item.ok else 'FAIL'} | "
                f"{'ok' if item.provider_ok else 'fail'} | {'ok' if item.sections_ok else 'fail'} | "
                f"{'ok' if item.trace_ok else 'fail'} | {'ok' if item.runtime_ok else 'fail'} | "
                f"{'ok' if item.knowledge_ok else 'fail'} | {notes} |"
            )

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- Passed: `{len(passed)}`",
                f"- Blocked: `{len(blocked)}`",
                f"- Degraded: `{len(degraded)}`",
                "",
                "## Next fixes",
                "",
            ]
        )

        next_fixes: list[str] = []
        if self.knowledge_doc_status and self.knowledge_doc_status.get("status") != "ready":
            next_fixes.append("Investigate NVIDIA embedding model compatibility or add an explicit embedding fallback path.")
        if blocked:
            next_fixes.append("Resolve provider-level blockers before claiming NVIDIA Build as the default free test path.")
        if degraded:
            next_fixes.append("Tighten chat/runtime/logs consistency for scenarios that returned partial trace coverage.")
        if any("cannot access the requested workspace path" in " ".join(item.notes).lower() for item in self.results):
            next_fixes.append(
                "For Docker-based validation, mount each target repo into the worker container or run the CLI worker on the host so workspace paths are executable."
            )
        if not next_fixes:
            next_fixes.append("Promote the NVIDIA Build setup flow into README/provider docs and keep monitoring free-tier stability.")
        lines.extend(f"- {item}" for item in next_fixes)
        lines.append("")

        self.report_path.write_text("\n".join(lines), encoding="utf-8")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    api_key = require_env("DREAMAXIS_NVIDIA_API_KEY")
    chat_model = os.environ.get("DREAMAXIS_NVIDIA_CHAT_MODEL", "qwen/qwen3-coder-480b-a35b-instruct")
    embedding_model = os.environ.get("DREAMAXIS_NVIDIA_EMBEDDING_MODEL", "nvidia/llama-3.2-nv-embedqa-1b-v2")
    report_path = Path(os.environ.get("DREAMAXIS_VALIDATION_REPORT", r"D:\DreamAxis\dreamaxis\docs\chat-acceptance-report-nvidia.md"))

    validator = DreamAxisValidator(
        base_url=os.environ.get("DREAMAXIS_API_BASE_URL", "http://127.0.0.1:8000"),
        api_key=api_key,
        chat_model=chat_model,
        embedding_model=embedding_model,
        report_path=report_path,
    )
    validator.run()
    print(f"Validation report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
