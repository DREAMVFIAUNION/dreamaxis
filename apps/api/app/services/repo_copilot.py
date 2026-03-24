from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.runtime_execution import RuntimeExecution
from app.models.skill_definition import SkillDefinition
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.message import ChatMode, KnowledgeChunkReference
from app.services.environment_doctor import build_doctor_result
from app.services.execution_annotations import build_annotation
from app.services.runtime_dispatcher import dispatch_browser_execution, dispatch_cli_execution
from app.services.runtime_registry import list_runtimes_for_workspace
from app.services.runtime_service import create_runtime_execution, mark_runtime_failed, mark_runtime_running, mark_runtime_succeeded


SCENARIO_LABELS = {
    "repo_onboarding": "Repo onboarding",
    "verify_local_readiness": "Verify local readiness",
    "trace_feature_or_bug": "Trace a feature or bug surface",
    "run_verification_workflow": "Run verification workflow",
    "knowledge_assisted_troubleshooting": "Knowledge-assisted troubleshooting",
}

MODE_LABELS: dict[ChatMode, str] = {
    "understand": "Understand",
    "inspect": "Inspect",
    "verify": "Verify",
    "propose_fix": "Propose fix",
}

FAILURE_CLASSIFICATION_LABELS = {
    "dependency_or_install": "Dependency / install",
    "missing_toolchain": "Missing toolchain",
    "repo_not_ready": "Repo not ready",
    "script_or_manifest_missing": "Script / manifest missing",
    "code_or_config_failure": "Code / config failure",
    "browser_or_runtime_failure": "Browser / runtime failure",
    "unknown": "Unknown",
}

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
REPO_COPILOT_HEADINGS = [
    "## Intent / plan",
    "## What ran",
    "## What was found",
    "## Recommended next step",
]


@dataclass(slots=True)
class PlannedStep:
    kind: str
    title: str
    summary: str
    command: str | None = None
    actions: list[dict[str, Any]] | None = None
    working_directory: str | None = None


def _timeline_status(step_status: str) -> str:
    if step_status in {"failed", "error", "missing"}:
        return "failed"
    if step_status in {"running", "queued"}:
        return step_status
    return "succeeded"


def _shorten(value: str | None, limit: int = 1400) -> str:
    if not value:
        return ""
    normalized = ANSI_ESCAPE_RE.sub("", value).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n...[truncated]"


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _extract_quoted_target(prompt: str) -> str | None:
    for pattern in [r"`([^`]+)`", r'"([^"]+)"', r"'([^']+)'"]:
        match = re.search(pattern, prompt)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return None


def _extract_route(prompt: str) -> str | None:
    match = re.search(r"(?<![A-Za-z0-9])(/[A-Za-z0-9._~!$&'()*+,;=:@%/\-]+)", prompt)
    if not match:
        return None
    route = match.group(1).strip().rstrip(".,)")
    return route if route.startswith("/") else None


def _normalize_search_candidate(candidate: str | None) -> str | None:
    if not isinstance(candidate, str):
        return None
    cleaned = re.sub(r"\s+", " ", candidate).strip().strip("`'\"").strip(".,:;()[]{}")
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered in {"the", "a", "an", "this", "that", "these", "those"}:
        return None
    if lowered.startswith(("the ", "a ", "an ")):
        parts = cleaned.split(" ", 1)
        if len(parts) == 2:
            cleaned = parts[1].strip()
            lowered = cleaned.lower()
    return cleaned or None


def extract_target_url(prompt: str) -> str | None:
    url_match = re.search(r"https?://[^\s)]+", prompt, flags=re.IGNORECASE)
    if url_match:
        return url_match.group(0).rstrip(".,)")
    route = _extract_route(prompt)
    if route:
        return f"http://localhost:3000{route}"
    return None


def extract_search_term(prompt: str) -> str | None:
    quoted = _extract_quoted_target(prompt)
    if quoted:
        normalized = _normalize_search_candidate(quoted)
        if normalized:
            return normalized

    route = _extract_route(prompt)
    if route:
        return route

    lowered = prompt.lower()
    for phrase in [
        "manifest inventory",
        "workspace root snapshot",
        "readme",
        "dashboard",
        "provider connection",
        "runtime execution",
        "lint",
        "build",
        "test",
    ]:
        if phrase in lowered:
            return phrase

    patterns = [
        r"(?:where is|where does|trace|find|inspect|search for|look for)\s+(?:the\s+|a\s+|an\s+)?([A-Za-z0-9_./\-\s]+?)(?:[?.!,]|$)",
        r"(?:error|failed|exception|bug|issue)\s+(?:for|in|with)?\s*(?:the\s+|a\s+|an\s+)?([A-Za-z0-9_./\-\s]+?)(?:[?.!,]|$)",
        r"(?:page|route|module|handler|api)\s+(?:the\s+|a\s+|an\s+)?([A-Za-z0-9_./\-\s]+?)(?:[?.!,]|$)",
    ]
    lowered_prompt = prompt.strip()
    for pattern in patterns:
        match = re.search(pattern, lowered_prompt, flags=re.IGNORECASE)
        if match:
            candidate = _normalize_search_candidate(match.group(1))
            if candidate:
                return candidate
    return None


def infer_mode_from_scenario(scenario_tag: str) -> ChatMode:
    if scenario_tag == "repo_onboarding":
        return "understand"
    if scenario_tag == "trace_feature_or_bug":
        return "inspect"
    if scenario_tag in {"verify_local_readiness", "run_verification_workflow"}:
        return "verify"
    return "propose_fix"


def classify_repo_copilot_scenario(prompt: str, mode: ChatMode | None = None) -> tuple[str, str, ChatMode]:
    lowered = prompt.lower()
    if mode == "understand":
        return "repo_onboarding", "Using understand mode to produce a repo-grounded orientation pass.", mode
    if mode == "inspect":
        return "trace_feature_or_bug", "Using inspect mode to trace files, routes, handlers, or repo surfaces.", mode
    if mode == "propose_fix":
        return "knowledge_assisted_troubleshooting", "Using propose-fix mode to gather evidence and prepare a repair proposal.", mode
    if mode == "verify":
        if any(token in lowered for token in ["doctor", "environment", "readiness", "missing", "install", "dependency", "prerequisite", "setup ready"]):
            return "verify_local_readiness", "Using verify mode to inspect machine and workspace readiness.", mode
        return "run_verification_workflow", "Using verify mode to run safe verification probes and collect evidence.", mode

    if any(token in lowered for token in ["error", "failed", "exception", "stack trace", "bug", "issue", "why does", "why did"]):
        return "knowledge_assisted_troubleshooting", "The prompt references a failure or troubleshooting path.", "propose_fix"
    if any(token in lowered for token in ["doctor", "environment", "readiness", "missing", "install", "dependency", "prerequisite", "setup ready"]):
        return "verify_local_readiness", "The prompt is asking whether the local machine or workspace is ready.", "verify"
    if any(token in lowered for token in ["where is", "where does", "trace", "which file", "which module", "handler", "flow", "route", "api path"]):
        return "trace_feature_or_bug", "The prompt is asking to locate or trace a feature path through the repo.", "inspect"
    if any(token in lowered for token in ["verify", "check", "lint", "build", "smoke", "screenshot", "page works", "ui works", "run tests", "test this"]):
        return "run_verification_workflow", "The prompt is asking for an execution-backed verification workflow.", "verify"
    if any(token in lowered for token in ["what is this repo", "how do i start", "how does this start", "main module", "entry point", "key dependency", "repo summary"]):
        return "repo_onboarding", "The prompt is asking for a repo onboarding summary.", "understand"
    return "repo_onboarding", "Defaulting to repo onboarding for a general repository understanding request.", "understand"


def _doctor_summary_label(doctor_result: dict[str, Any]) -> str:
    machine_status = ((doctor_result.get("machine_summary") or {}).get("status")) or "unknown"
    workspace_status = ((doctor_result.get("workspace") or {}).get("status")) or "unknown"
    return f"Machine readiness is {machine_status}; workspace readiness is {workspace_status}."


def build_intent_plan(
    scenario_tag: str,
    *,
    mode: ChatMode,
    search_term: str | None,
    browser_url: str | None,
) -> list[str]:
    if scenario_tag == "verify_local_readiness":
        return [
            "Check machine baseline and workspace readiness via the environment doctor.",
            "Inspect repository manifests that affect execution or setup.",
            "Call out missing capabilities and concrete install or repair hints.",
        ]
    if scenario_tag == "trace_feature_or_bug":
        return [
            f"Search the repo for `{search_term}`." if search_term else "Search the repo for the feature or route surface described in the prompt.",
            "Cross-check the likely code path against architecture and API knowledge when available.",
            "Return the most relevant file and route evidence instead of a generic summary.",
        ]
    if scenario_tag == "run_verification_workflow":
        items = [
            "Run safe verification probes such as lint/build or other read-only checks.",
            "Capture runtime output and failure points as evidence.",
        ]
        if browser_url:
            items.append(f"Open `{browser_url}` in the browser runtime and capture page evidence.")
        return items
    if scenario_tag == "knowledge_assisted_troubleshooting":
        items = [
            "Collect the most relevant local error or code evidence from the workspace.",
            "Blend repo evidence with knowledge references where they help explain the failure.",
            "Recommend the next debugging move instead of guessing beyond the evidence.",
        ]
        if mode == "propose_fix":
            items.append("Turn the evidence into a proposal-only repair plan without mutating files.")
        return items
    return [
        "Inspect the workspace layout and startup manifests.",
        "Preview the primary README or architecture notes for grounding.",
        "Summarize entrypoints, key modules, and likely launch commands with citations to local files.",
    ]


def _build_readiness_probe() -> PlannedStep:
    return PlannedStep(
        kind="cli",
        title="Manifest inventory",
        summary="Inspect startup and dependency manifests that define how the workspace is launched.",
        command=(
            "$paths = @('package.json','pnpm-workspace.yaml','pyproject.toml','requirements.txt','requirements-dev.txt',"
            "'Dockerfile','docker-compose.yml','docker-compose.yaml','infrastructure\\docker\\docker-compose.yml'); "
            "$results = foreach ($path in $paths) { if (Test-Path $path) { Get-Item $path | Select-Object Name, FullName } }; "
            "if ($results) { $results } else { 'No startup manifests found.' }"
        ),
        working_directory=".",
    )


def _build_repo_onboarding_steps() -> list[PlannedStep]:
    return [
        PlannedStep(
            kind="cli",
            title="Workspace root snapshot",
            summary="List top-level files and directories to anchor the repo summary.",
            command="Get-ChildItem -Force | Select-Object Mode,Length,Name",
            working_directory=".",
        ),
        PlannedStep(
            kind="cli",
            title="Entry manifest inventory",
            summary="Locate the main README, package manifests, and architecture docs.",
            command=(
                "$paths = @('README.md','package.json','pnpm-workspace.yaml','pyproject.toml','docs\\architecture.md',"
                "'infrastructure\\docker\\docker-compose.yml'); "
                "$results = foreach ($path in $paths) { if (Test-Path $path) { Get-Item $path | Select-Object FullName } }; "
                "if ($results) { $results } else { 'No entry manifests found.' }"
            ),
            working_directory=".",
        ),
        PlannedStep(
            kind="cli",
            title="README or architecture preview",
            summary="Read the first section of the primary repo docs for grounded onboarding context.",
            command=(
                "if (Test-Path README.md) { Get-Content README.md -TotalCount 80 } "
                "elseif (Test-Path docs\\architecture.md) { Get-Content docs\\architecture.md -TotalCount 80 } "
                "else { 'No README.md or docs/architecture.md found.' }"
            ),
            working_directory=".",
        ),
    ]


def _build_trace_steps(search_term: str | None) -> list[PlannedStep]:
    if not search_term:
        return [
            PlannedStep(
                kind="cli",
                title="Repository surface scan",
                summary="List likely source directories because no focused search term was provided.",
                command="Get-ChildItem -Directory -Force | Select-Object Name,FullName",
                working_directory=".",
            )
        ]

    quoted = _powershell_quote(search_term)
    return [
        PlannedStep(
            kind="cli",
            title="Code search",
            summary=f"Search recursively for references to `{search_term}`.",
            command=(
                f"$matches = Get-ChildItem -Recurse -File | Select-String -SimpleMatch -Pattern {quoted}; "
                "if ($matches) { $matches | Select-Object -First 40 Path, LineNumber, Line } "
                "else { 'No code matches found.' }"
            ),
            working_directory=".",
        ),
        PlannedStep(
            kind="cli",
            title="Filename scan",
            summary=f"Look for files whose names are related to `{search_term}`.",
            command=(
                f"$term = {quoted}; "
                "$matches = Get-ChildItem -Recurse -File | Where-Object { $_.Name -like ('*' + $term + '*') }; "
                "if ($matches) { $matches | Select-Object -First 30 FullName } "
                "else { 'No matching filenames found.' }"
            ),
            working_directory=".",
        ),
    ]


def _build_verify_manifest_probe() -> PlannedStep:
    return PlannedStep(
        kind="cli",
        title="Verification manifest probe",
        summary="Inspect repo markers, package manager signals, and available scripts before choosing verification commands.",
        command=(
            "$hasPackageJson = Test-Path package.json; "
            "$hasPnpmLock = Test-Path pnpm-lock.yaml; "
            "$hasPackageLock = Test-Path package-lock.json; "
            "$hasPyproject = Test-Path pyproject.toml; "
            "$hasRequirements = (Test-Path requirements.txt) -or (Test-Path requirements-dev.txt) -or (Test-Path setup.py); "
            "$packageManager = if ($hasPnpmLock) { 'pnpm' } elseif ($hasPackageLock) { 'npm' } elseif ($hasPackageJson) { 'npm' } else { 'none' }; "
            "$scripts = @(); "
            "if ($hasPackageJson) { "
            "  try { "
            "    $pkg = Get-Content package.json -Raw | ConvertFrom-Json; "
            "    if ($pkg.scripts) { $scripts = $pkg.scripts.PSObject.Properties.Name } "
            "  } catch { $scripts = @('__parse_error__') } "
            "} "
            "[pscustomobject]@{ "
            "  package_json = $hasPackageJson; "
            "  pnpm_lock = $hasPnpmLock; "
            "  package_lock = $hasPackageLock; "
            "  package_manager = $packageManager; "
            "  scripts = ($scripts -join ', '); "
            "  pyproject = $hasPyproject; "
            "  python_markers = $hasRequirements "
            "} | Format-List"
        ),
        working_directory=".",
    )


def _node_script_probe_command(script_name: str) -> str:
    return (
        "$hasPackageJson = Test-Path package.json; "
        f"$scriptName = '{script_name}'; "
        "if (-not $hasPackageJson) { Write-Output 'SKIP: No package.json detected for a Node verification probe.'; exit 0 } "
        "try { $pkg = Get-Content package.json -Raw | ConvertFrom-Json } "
        "catch { Write-Output 'SKIP: package.json could not be parsed for script discovery.'; exit 0 } "
        "$scripts = @(); "
        "if ($pkg.scripts) { $scripts = $pkg.scripts.PSObject.Properties.Name } "
        "if (-not ($scripts -contains $scriptName)) { Write-Output ('SKIP: package.json has no ' + $scriptName + ' script.'); exit 0 } "
        "$pnpm = Get-Command pnpm -ErrorAction SilentlyContinue; "
        "$npm = Get-Command npm -ErrorAction SilentlyContinue; "
        "if ((Test-Path pnpm-lock.yaml) -and $pnpm) { "
        "  Write-Output ('Running pnpm ' + $scriptName + ' because pnpm-lock.yaml is present.'); "
        "  & pnpm $scriptName; "
        "} elseif ($npm) { "
        "  Write-Output ('Running npm run ' + $scriptName + ' as the available fallback.'); "
        "  & npm run $scriptName --if-present; "
        "} else { "
        "  Write-Output 'SKIP: Neither pnpm nor npm is available in PATH.'; "
        "  exit 0 "
        "}"
    )


def _python_test_probe_command() -> str:
    return (
        "$hasPythonProject = (Test-Path pyproject.toml) -or (Test-Path requirements.txt) -or (Test-Path requirements-dev.txt) -or (Test-Path setup.py); "
        "if (-not $hasPythonProject) { Write-Output 'SKIP: No Python project markers detected.'; exit 0 } "
        "$python = Get-Command python -ErrorAction SilentlyContinue; "
        "if (-not $python) { Write-Output 'SKIP: Python is not available in PATH.'; exit 0 } "
        "$hasPytestConfig = (Test-Path pytest.ini) -or (Test-Path pyproject.toml) -or (Test-Path tox.ini); "
        "$hasTestsDir = Test-Path tests; "
        "$hasTestFiles = [bool](Get-ChildItem -Recurse -File -Include 'test_*.py','*_test.py' -ErrorAction SilentlyContinue | Select-Object -First 1); "
        "if (-not ($hasPytestConfig -or $hasTestsDir -or $hasTestFiles)) { "
        "  Write-Output 'SKIP: Python project detected but no pytest markers or tests were found.'; "
        "  exit 0 "
        "} "
        "Write-Output 'Running python -m pytest -q because Python test markers were detected.'; "
        "& python -m pytest -q"
    )


def _build_verify_steps(prompt: str, browser_url: str | None) -> list[PlannedStep]:
    lowered = prompt.lower()
    steps: list[PlannedStep] = [_build_verify_manifest_probe()]
    wants_tests = "test" in lowered or "pytest" in lowered
    if any(token in lowered for token in ["lint", "build", "check", "verify", "run"]):
        steps.extend(
            [
                PlannedStep(
                    kind="cli",
                    title="Lint probe",
                    summary="Run a repo-aware lint probe using the detected package manager when a lint script exists.",
                    command=_node_script_probe_command("lint"),
                    working_directory=".",
                ),
                PlannedStep(
                    kind="cli",
                    title="Build probe",
                    summary="Run a repo-aware build probe using the detected package manager when a build script exists.",
                    command=_node_script_probe_command("build"),
                    working_directory=".",
                ),
            ]
        )
    if wants_tests:
        steps.extend(
            [
                PlannedStep(
                    kind="cli",
                    title="Test probe",
                    summary="Run a repo-aware Node test probe when a test script exists.",
                    command=_node_script_probe_command("test"),
                    working_directory=".",
                ),
                PlannedStep(
                    kind="cli",
                    title="Python test probe",
                    summary="Run a Python test probe when Python project markers and pytest-style tests are present.",
                    command=_python_test_probe_command(),
                    working_directory=".",
                ),
            ]
        )
    if browser_url:
        steps.append(
            PlannedStep(
                kind="browser",
                title="Browser capture",
                summary=f"Open `{browser_url}` and capture page text plus a screenshot artifact.",
                actions=[
                    {"action": "open_url", "url": browser_url},
                    {"action": "wait_for", "time": 1.5},
                    {"action": "extract_text"},
                    {"action": "take_screenshot", "name": "repo-copilot-verify"},
                ],
            )
        )
    if not steps:
        steps.append(_build_readiness_probe())
    return steps


def _build_troubleshooting_steps(prompt: str, search_term: str | None, browser_url: str | None) -> list[PlannedStep]:
    steps: list[PlannedStep] = []
    if search_term:
        steps.extend(_build_trace_steps(search_term)[:1])

    lowered = prompt.lower()
    if "lint" in lowered:
        steps.append(
            PlannedStep(
                kind="cli",
                title="Lint replay",
                summary="Replay lint with repo-aware package-manager detection to reproduce the reported failure surface.",
                command=_node_script_probe_command("lint"),
                working_directory=".",
            )
        )
    if "build" in lowered:
        steps.append(
            PlannedStep(
                kind="cli",
                title="Build replay",
                summary="Replay build with repo-aware package-manager detection to gather fresh failure output.",
                command=_node_script_probe_command("build"),
                working_directory=".",
            )
        )
    if "test" in lowered:
        steps.append(
            PlannedStep(
                kind="cli",
                title="Test replay",
                summary="Replay tests with repo-aware Node script detection when available.",
                command=_node_script_probe_command("test"),
                working_directory=".",
            )
        )
        steps.append(
            PlannedStep(
                kind="cli",
                title="Python test replay",
                summary="Replay Python tests when pytest-style markers are present.",
                command=_python_test_probe_command(),
                working_directory=".",
            )
        )
    if browser_url:
        steps.append(
            PlannedStep(
                kind="browser",
                title="Browser failure capture",
                summary=f"Open `{browser_url}` and capture browser evidence around the reported issue.",
                actions=[
                    {"action": "open_url", "url": browser_url},
                    {"action": "wait_for", "time": 1.5},
                    {"action": "extract_text"},
                    {"action": "take_screenshot", "name": "repo-copilot-troubleshoot"},
                ],
            )
        )
    if not steps:
        steps.extend(
            [
                _build_readiness_probe(),
                PlannedStep(
                    kind="cli",
                    title="Workspace root snapshot",
                    summary="Capture a top-level workspace snapshot so the repair proposal stays tied to real repo surfaces.",
                    command="Get-ChildItem -Force | Select-Object Mode,Length,Name",
                    working_directory=".",
                ),
            ]
        )
    return steps


def build_planned_steps(
    scenario_tag: str,
    *,
    prompt: str,
    search_term: str | None,
    browser_url: str | None,
) -> list[PlannedStep]:
    if scenario_tag == "verify_local_readiness":
        return [_build_readiness_probe()]
    if scenario_tag == "trace_feature_or_bug":
        return _build_trace_steps(search_term)
    if scenario_tag == "run_verification_workflow":
        return _build_verify_steps(prompt, browser_url)
    if scenario_tag == "knowledge_assisted_troubleshooting":
        return _build_troubleshooting_steps(prompt, search_term, browser_url)
    return _build_repo_onboarding_steps()


def _dedupe_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for raw in lines:
        line = _shorten(raw, limit=220).strip()
        if not line:
            continue
        normalized = line.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(line)
    return deduped


def _extract_high_signal_lines(*texts: str | None, limit: int = 3) -> list[str]:
    priority_patterns = [
        "traceback",
        "exception",
        "error:",
        "error ",
        "failed",
        "cannot find module",
        "module not found",
        "no module named",
        "not available in path",
        "not recognized",
        "err_",
        "elifecycle",
        "missing",
        "not found",
        "skip:",
    ]
    priority_lines: list[str] = []
    fallback_lines: list[str] = []
    for text in texts:
        if not text:
            continue
        cleaned = _shorten(text, limit=1800)
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            if any(token in lowered for token in priority_patterns):
                priority_lines.append(line)
            else:
                fallback_lines.append(line)

    combined = _dedupe_lines(priority_lines) + _dedupe_lines(fallback_lines)
    return combined[:limit]


def _extract_primary_failure_target(step: dict[str, Any], highlights: list[str]) -> str | None:
    raw_payload = step.get("raw_payload") if isinstance(step.get("raw_payload"), dict) else {}

    for candidate in [
        step.get("current_url"),
        step.get("path"),
        step.get("cwd"),
        raw_payload.get("current_url"),
        raw_payload.get("path"),
        raw_payload.get("cwd"),
    ]:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    for text in [
        step.get("summary"),
        raw_payload.get("summary"),
        step.get("title"),
        raw_payload.get("title"),
        *highlights,
    ]:
        if isinstance(text, str) and text.strip():
            quoted = _normalize_search_candidate(_extract_quoted_target(text))
            if quoted:
                return quoted

    command_sources = [
        step.get("command_preview"),
        step.get("payload_preview"),
        step.get("target_label"),
        raw_payload.get("command_preview"),
    ]
    for command_preview in command_sources:
        if not isinstance(command_preview, str) or not command_preview.strip():
            continue
        manifest_match = re.search(
            r"(package\.json|pnpm-workspace\.yaml|pyproject\.toml|requirements(?:-dev)?\.txt|Dockerfile|docker-compose(?:\.ya?ml)?|README\.md)",
            command_preview,
            flags=re.IGNORECASE,
        )
        if manifest_match:
            return manifest_match.group(1)

        quoted = _normalize_search_candidate(_extract_quoted_target(command_preview))
        if quoted:
            return quoted

    for line in highlights:
        url_match = re.search(r"https?://[^\s`'\"]+", line, flags=re.IGNORECASE)
        if url_match:
            return url_match.group(0).rstrip(".,)")

        path_match = re.search(
            r"([A-Za-z0-9_./\\-]+(?:package\.json|pnpm-workspace\.yaml|pyproject\.toml|requirements(?:-dev)?\.txt|Dockerfile|docker-compose(?:\.ya?ml)?|README\.md))",
            line,
            flags=re.IGNORECASE,
        )
        if path_match:
            return path_match.group(1)

    return None


def _classify_failure(
    step: dict[str, Any],
    *,
    doctor_result: dict[str, Any],
) -> str:
    output = " ".join(
        str(value or "")
        for value in [
            step.get("title"),
            step.get("summary"),
            step.get("output_excerpt"),
            step.get("stderr_excerpt"),
            step.get("command_preview"),
            step.get("current_url"),
        ]
    ).lower()
    machine_summary = doctor_result.get("machine_summary") or {}
    workspace_summary = (doctor_result.get("workspace") or {}).get("summary") or {}
    missing_required = [str(item).lower() for item in workspace_summary.get("missing_required", [])]
    install_guidance = [str(item).lower() for item in (doctor_result.get("install_guidance") or [])]

    if step.get("kind") == "browser" or any(
        token in output for token in ["http://", "https://", "err_connection", "navigation timeout", "page.goto", "browser", "playwright"]
    ):
        return "browser_or_runtime_failure"

    if any(
        token in output
        for token in [
            "neither pnpm nor npm is available",
            "python is not available in path",
            "not available in path",
            "not recognized as an internal or external command",
            "command not found",
            "is not installed",
        ]
    ):
        return "missing_toolchain"

    if any(token in output for token in ["cannot find module", "module not found", "no module named", "importerror", "modulenotfounderror", "elifecycle"]):
        return "dependency_or_install"

    if any(token in output for token in ["no package.json detected", "no python project markers detected", "no startup manifests found"]):
        return "repo_not_ready"

    if any(token in output for token in ["has no", "script discovery", "__parse_error__", "no entry manifests found", "manifest inventory"]):
        return "script_or_manifest_missing"

    if machine_summary.get("status") in {"degraded", "missing"} and (
        missing_required or any("install" in item for item in install_guidance)
    ):
        return "missing_toolchain"

    if any(token in output for token in ["syntaxerror", "typeerror", "referenceerror", "valueerror", "assertionerror", "failed with exit code", "application error"]):
        return "code_or_config_failure"

    if step.get("kind") == "cli" and step.get("exit_code") not in {None, 0}:
        return "code_or_config_failure"

    return "unknown"


def _build_failure_summary(
    step: dict[str, Any],
    *,
    classification: str,
    highlights: list[str],
    failed_steps: list[dict[str, Any]],
) -> str:
    title = str(step.get("title") or "Execution step")
    base = {
        "dependency_or_install": f"{title} failed because the workspace appears to be missing required dependencies or install artifacts.",
        "missing_toolchain": f"{title} failed because the required local toolchain is not available in the active runtime.",
        "repo_not_ready": f"{title} could not run because this workspace is missing the repo markers needed for the requested verification path.",
        "script_or_manifest_missing": f"{title} could not run because the expected script or manifest entrypoint is missing.",
        "code_or_config_failure": f"{title} reached the repo command path but failed inside code or configuration execution.",
        "browser_or_runtime_failure": f"{title} failed in the browser/runtime layer instead of a repo script path.",
        "unknown": f"{title} failed, but the captured evidence is not yet specific enough to classify it more narrowly.",
    }[classification]

    pieces = [base]
    if highlights:
        pieces.append(f"Key signal: `{highlights[0]}`.")

    related = [str(item.get("title") or "") for item in failed_steps if item is not step and item.get("title")]
    if related:
        pieces.append(f"Related failed probes: {', '.join(related[:2])}.")
    return " ".join(pieces)


def _build_failure_reasoning(
    step: dict[str, Any],
    *,
    classification: str,
    highlights: list[str],
    doctor_result: dict[str, Any],
) -> list[str]:
    reasoning: list[str] = []
    title = str(step.get("title") or "Execution step")
    command = step.get("command_preview")
    if isinstance(command, str) and command:
        reasoning.append(f"{title} ran `{_shorten(command, limit=120)}` and exited with code {step.get('exit_code', '--')}.")
    elif step.get("current_url"):
        reasoning.append(f"{title} targeted `{step.get('current_url')}` and returned a failed browser/runtime result.")

    if highlights:
        reasoning.append(f"The highest-signal captured line was `{highlights[0]}`.")

    classification_reason = {
        "dependency_or_install": "That signal points to a dependency or install gap rather than a feature-level regression.",
        "missing_toolchain": "That pattern usually means the runtime is missing the required executable instead of the repo logic being broken.",
        "repo_not_ready": "The probe could not find the repo markers needed to run the requested verification flow from this workspace root.",
        "script_or_manifest_missing": "The repo surface exists, but the expected script or manifest entrypoint was not present for this verification path.",
        "code_or_config_failure": "The command started correctly, so the failure is more likely inside repo code or configuration than local tool discovery.",
        "browser_or_runtime_failure": "The failure surfaced in browser navigation, page capture, or runtime infrastructure rather than a pure CLI script path.",
        "unknown": "The evidence shows a failure, but the captured output is still too generic to narrow it further.",
    }[classification]
    reasoning.append(classification_reason)

    install_guidance = doctor_result.get("install_guidance") or []
    if classification in {"missing_toolchain", "repo_not_ready"} and install_guidance:
        reasoning.append(f"Doctor guidance already points at the next repair lane: {install_guidance[0]}")

    return _dedupe_lines(reasoning)[:4]


def analyze_failure_state(
    *,
    doctor_result: dict[str, Any],
    trace_steps: list[dict[str, Any]],
) -> dict[str, Any] | None:
    failed_steps = [step for step in trace_steps if step.get("status") == "failed"]
    if not failed_steps:
        return None

    primary = failed_steps[0]
    highlights = _extract_high_signal_lines(
        str(primary.get("stderr_excerpt") or ""),
        str(primary.get("output_excerpt") or ""),
        str(primary.get("summary") or ""),
        str(primary.get("command_preview") or ""),
    )
    if not highlights:
        fallback_label = str(primary.get("summary") or primary.get("title") or "Failed execution step").strip()
        if fallback_label:
            highlights = [fallback_label]
    classification = _classify_failure(primary, doctor_result=doctor_result)
    primary_target = _extract_primary_failure_target(primary, highlights)
    return {
        "failed_step_title": primary.get("title"),
        "failed_step_kind": primary.get("kind"),
        "primary_runtime_execution_id": primary.get("runtime_execution_id"),
        "primary_failure_target": primary_target,
        "failure_classification": classification,
        "failure_summary": _build_failure_summary(primary, classification=classification, highlights=highlights, failed_steps=failed_steps),
        "stderr_highlights": highlights,
        "grounded_next_step_reasoning": _build_failure_reasoning(
            primary,
            classification=classification,
            highlights=highlights,
            doctor_result=doctor_result,
        ),
        "failed_step_count": len(failed_steps),
    }


def build_recommended_next_actions(
    scenario_tag: str,
    *,
    doctor_result: dict[str, Any],
    trace_steps: list[dict[str, Any]],
    search_term: str | None,
    failure_state: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    machine_summary = doctor_result.get("machine_summary") or {}
    workspace = doctor_result.get("workspace") or {}
    install_guidance = doctor_result.get("install_guidance") or []
    failed_step = next((step for step in trace_steps if step.get("status") == "failed"), None)

    actions: list[dict[str, str]] = []
    if machine_summary.get("status") in {"degraded", "missing"} or workspace.get("status") in {"degraded", "missing"}:
        if install_guidance:
            actions.append({"label": install_guidance[0], "reason": "Local readiness is not fully satisfied."})

    if failure_state:
        classification = str(failure_state.get("failure_classification") or "unknown")
        primary_target = str(failure_state.get("primary_failure_target") or "").strip()
        if classification == "dependency_or_install":
            actions.append(
                {
                    "label": f"Restore dependencies around {primary_target}, then rerun the same verification probe." if primary_target else "Restore workspace dependencies, then rerun the same verification probe.",
                    "reason": failure_state.get("failure_summary") or "The failure looks like an install or dependency gap.",
                }
            )
        elif classification == "missing_toolchain":
            actions.append(
                {
                    "label": install_guidance[0] if install_guidance else "Install the missing local toolchain, then rerun the probe.",
                    "reason": failure_state.get("failure_summary") or "The active runtime is missing the required executable.",
                }
            )
        elif classification == "script_or_manifest_missing":
            actions.append(
                {
                    "label": f"Confirm the expected script or manifest entrypoint around {primary_target} before retrying." if primary_target else "Confirm the expected script or manifest entrypoint before retrying this lane.",
                    "reason": failure_state.get("failure_summary") or "The repo does not expose the expected verification entrypoint.",
                }
            )
        elif classification == "repo_not_ready":
            actions.append(
                {
                    "label": f"Fix the workspace binding around {primary_target} before retrying." if primary_target else "Point DreamAxis at the correct repo root or add the missing workspace markers before retrying.",
                    "reason": failure_state.get("failure_summary") or "The workspace root does not match the requested verification path yet.",
                }
            )
        elif classification == "browser_or_runtime_failure":
            actions.append(
                {
                    "label": f"Open the failing runtime capture for {primary_target} and confirm the route or page is reachable." if primary_target else "Open the failing runtime capture and confirm the local route or page is reachable.",
                    "reason": failure_state.get("failure_summary") or "The failure came from the browser/runtime layer.",
                }
            )
        else:
            actions.append(
                {
                    "label": "Inspect the failing command output and narrow the next debugging step to that specific failure surface.",
                    "reason": failure_state.get("failure_summary") or "At least one captured probe failed.",
                }
            )

    if failed_step:
        actions.append(
            {
                "label": f"Inspect runtime execution {failed_step.get('runtime_execution_id') or failed_step.get('title')}",
                "reason": "At least one execution probe failed and needs a closer look.",
            }
        )

    if scenario_tag == "repo_onboarding":
        actions.append(
            {
                "label": "Ask DreamAxis to trace a specific route, module, or API next.",
                "reason": "The onboarding snapshot should narrow the next question to a concrete code path.",
            }
        )
    elif scenario_tag == "verify_local_readiness":
        actions.append(
            {
                "label": "Fix the missing baseline items, then rerun the readiness check.",
                "reason": "Readiness answers are only as strong as the local capability snapshot.",
            }
        )
    elif scenario_tag == "trace_feature_or_bug":
        actions.append(
            {
                "label": f"Open the top files returned for `{search_term}`." if search_term else "Open the most relevant files returned by the trace scan.",
                "reason": "The next step is to inspect the concrete code path rather than keep the trace abstract.",
            }
        )
    elif scenario_tag == "run_verification_workflow":
        actions.append(
            {
                "label": "Promote the failing probe into a focused fix or deeper runtime investigation.",
                "reason": "Verification should end with a concrete next move, not just a pass/fail state.",
            }
        )
    else:
        actions.append(
            {
                "label": "Provide the exact error line, route, or failing command if you want a narrower troubleshooting pass.",
                "reason": "Troubleshooting gets sharper when the next prompt points to a specific failure surface.",
            }
        )

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for action in actions:
        label = action["label"]
        if label in seen:
            continue
        seen.add(label)
        deduped.append(action)
    return deduped[:4]


def build_proposal(
    *,
    mode: ChatMode,
    scenario_tag: str,
    search_term: str | None,
    trace_steps: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    failure_state: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if mode != "propose_fix":
        return None

    suggested_commands: list[str] = []
    targets: list[dict[str, str]] = []
    risks = [
        "This is a proposal only; DreamAxis did not write files or execute any mutating command.",
        "Validate the suggested files and commands against the repo before applying changes.",
    ]
    prerequisites = [
        "Re-run the failing verification probe after applying the fix.",
        "Keep changes scoped to the workspace root and affected module chain.",
    ]

    for step in trace_steps:
        command_preview = step.get("command_preview")
        if isinstance(command_preview, str) and command_preview and command_preview not in suggested_commands:
            suggested_commands.append(command_preview)
        if step.get("status") == "failed":
            cwd = step.get("path") or step.get("cwd")
            if isinstance(cwd, str) and cwd:
                targets.append({"file_path": cwd, "reason": f"{step.get('title')} failed from this working directory."})

    for item in evidence:
        path = item.get("path")
        if isinstance(path, str) and path and all(existing["file_path"] != path for existing in targets):
            targets.append({"file_path": path, "reason": f"Evidence from {item.get('title')} references this path."})

    if search_term and all(existing["file_path"] != search_term for existing in targets):
        targets.insert(0, {"file_path": search_term, "reason": "The prompt pointed to this route, module, or symbol."})

    primary_failure_target = str(failure_state.get("primary_failure_target") or "").strip() if failure_state else ""
    if primary_failure_target and all(existing["file_path"] != primary_failure_target for existing in targets):
        targets.insert(
            0,
            {
                "file_path": primary_failure_target,
                "reason": "Troubleshooting identified this as the primary failure target to inspect first.",
            },
        )

    if not targets:
        failed_step = next((step for step in trace_steps if step.get("status") == "failed"), None)
        if isinstance(failed_step, dict):
            fallback_target = (
                failed_step.get("current_url")
                or failed_step.get("cwd")
                or failed_step.get("path")
                or "(workspace root / runtime binding)"
            )
            targets.append(
                {
                    "file_path": str(fallback_target),
                    "reason": f"{failed_step.get('title') or 'The failing step'} did not expose a narrower file target, so start from this failure surface.",
                }
            )

    failed_titles = [step.get("title") for step in trace_steps if step.get("status") == "failed"]
    summary = (
        str(failure_state.get("failure_summary"))
        if failure_state and failure_state.get("failure_summary")
        else (
            "Collected runtime evidence and converted it into a grounded repair proposal."
            if failed_titles
            else "Collected repository evidence and prepared a proposal-only next repair pass."
        )
    )
    patch_summary_parts = []
    if search_term:
        patch_summary_parts.append(f"Focus the repair on `{search_term}` and its surrounding module chain.")
    if failed_titles:
        patch_summary_parts.append(f"Start with the failing probes: {', '.join(str(title) for title in failed_titles if title)}.")
    else:
        patch_summary_parts.append("Start with the files surfaced by the trace and verification evidence.")
    patch_summary = " ".join(patch_summary_parts)

    diff_preview = None
    if targets:
        target_list = "\n".join(f"- {item['file_path']}: {item['reason']}" for item in targets[:4])
        diff_preview = (
            "Proposed patch focus:\n"
            f"{target_list}\n"
            "- Apply the smallest change that resolves the captured failure while preserving existing verified behavior."
        )

    if failure_state and failure_state.get("grounded_next_step_reasoning"):
        patch_summary = f"{patch_summary} {' '.join(str(item) for item in failure_state['grounded_next_step_reasoning'][:2])}".strip()

    return {
        "status": "proposal_only",
        "summary": summary,
        "targets": targets[:6],
        "suggested_commands": suggested_commands[:6],
        "patch_summary": patch_summary,
        "diff_preview": diff_preview,
        "prerequisites": prerequisites,
        "risks": risks,
        "not_applied": True,
        "scenario_tag": scenario_tag,
    }


def summarize_artifacts(artifacts: Any) -> list[dict[str, Any]]:
    if not isinstance(artifacts, list):
        return []
    summaries: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        summaries.append(
            {
                "kind": artifact.get("kind"),
                "name": artifact.get("name"),
                "mime_type": artifact.get("mime_type"),
                "tabs": artifact.get("tabs"),
            }
        )
    return summaries


def build_repo_copilot_response_prompt(trace: dict[str, Any]) -> str:
    lines = [
        "You are DreamAxis in repo copilot mode for a solo developer.",
        "Use the execution trace and knowledge context as ground truth.",
        "Do not claim commands, screenshots, or findings that were not captured in the trace.",
        "If evidence is partial, say so plainly.",
        "No answer without evidence.",
        "Return exactly four markdown headings in this order:",
        *REPO_COPILOT_HEADINGS,
        "",
        f"Active mode: {trace.get('mode')}",
        f"Scenario: {trace.get('scenario_label')} ({trace.get('scenario_tag')})",
        f"Router reason: {trace.get('router_reason')}",
        "",
        "Intent plan:",
    ]
    for item in trace.get("intent_plan", []):
        lines.append(f"- {item}")

    readiness = trace.get("workspace_readiness") or {}
    machine_summary = trace.get("machine_summary") or {}
    lines.extend(
        [
            "",
            f"Machine readiness: {machine_summary.get('status', 'unknown')}",
            f"Workspace readiness: {readiness.get('status', 'unknown')}",
            "",
            "Execution trace:",
        ]
    )
    for index, step in enumerate(trace.get("steps", []), start=1):
        lines.append(
            f"{index}. [{step.get('kind')}] {step.get('title')} :: status={step.get('status')} :: summary={step.get('summary')}"
        )
        if step.get("command_preview"):
            lines.append(f"   command: {step.get('command_preview')}")
        if step.get("runtime_execution_id"):
            lines.append(f"   runtime_execution_id: {step.get('runtime_execution_id')}")
        if step.get("output_excerpt"):
            lines.append(f"   output_excerpt: {step.get('output_excerpt')}")

    evidence = trace.get("evidence") or []
    if evidence:
        lines.extend(["", "Evidence highlights:"])
        for item in evidence:
            lines.append(f"- {item.get('title')}: {item.get('content')}")

    failure_summary = trace.get("failure_summary")
    failure_classification = trace.get("failure_classification")
    primary_failure_target = trace.get("primary_failure_target")
    stderr_highlights = trace.get("stderr_highlights") or []
    grounded_reasoning = trace.get("grounded_next_step_reasoning") or []
    if failure_summary:
        lines.extend(
            [
                "",
                "Troubleshooting summary:",
                f"- failure_summary: {failure_summary}",
                f"- failure_type: {FAILURE_CLASSIFICATION_LABELS.get(str(failure_classification), str(failure_classification or 'Unknown'))}",
            ]
        )
        if primary_failure_target:
            lines.append(f"- primary_failure_target: {primary_failure_target}")
        if stderr_highlights:
            lines.append("- stderr_highlights:")
            for item in stderr_highlights:
                lines.append(f"  - {item}")
        if grounded_reasoning:
            lines.append("- grounded_next_step_reasoning:")
            for item in grounded_reasoning:
                lines.append(f"  - {item}")

    recommendations = trace.get("recommended_next_actions") or []
    if recommendations:
        lines.extend(["", "Recommended next actions:"])
        for item in recommendations:
            lines.append(f"- {item.get('label')}: {item.get('reason')}")

    proposal = trace.get("proposal")
    if isinstance(proposal, dict):
        lines.extend(
            [
                "",
                "Proposal metadata:",
                f"- status: {proposal.get('status')}",
                f"- summary: {proposal.get('summary')}",
                "- not_applied: true",
            ]
        )

    return "\n".join(lines)


def build_repo_copilot_fallback_response(trace: dict[str, Any]) -> str:
    sections = [
        REPO_COPILOT_HEADINGS[0],
        "\n".join(f"- {item}" for item in trace.get("intent_plan", [])) or "- No explicit plan was generated.",
        "",
        REPO_COPILOT_HEADINGS[1],
    ]

    ran = []
    for step in trace.get("steps", []):
        line = f"- [{step.get('kind')}] {step.get('title')} - {step.get('status')}: {step.get('summary')}"
        if step.get("runtime_execution_id"):
            line += f" (runtime {step['runtime_execution_id']})"
        ran.append(line)
    sections.append("\n".join(ran) or "- No runtime probes were executed.")

    sections.extend(["", REPO_COPILOT_HEADINGS[2]])
    failure_summary = trace.get("failure_summary")
    failure_classification = trace.get("failure_classification")
    primary_failure_target = trace.get("primary_failure_target")
    stderr_highlights = trace.get("stderr_highlights") or []
    grounded_reasoning = trace.get("grounded_next_step_reasoning") or []
    evidence = []
    if failure_summary:
        label = FAILURE_CLASSIFICATION_LABELS.get(str(failure_classification), str(failure_classification or "Unknown"))
        evidence.append(f"- Failure summary: {failure_summary}")
        evidence.append(f"- Failure type: {label}")
        if primary_failure_target:
            evidence.append(f"- Fix this first: {primary_failure_target}")
        for item in stderr_highlights[:3]:
            evidence.append(f"- Stderr highlight: {item}")
        for item in grounded_reasoning[:3]:
            evidence.append(f"- Why this likely failed: {item}")
    for item in trace.get("evidence", []):
        evidence.append(f"- {item.get('title')}: {item.get('content')}")
    sections.append("\n".join(evidence) or "- No grounded evidence was collected.")

    sections.extend(["", REPO_COPILOT_HEADINGS[3]])
    next_steps = []
    for item in trace.get("recommended_next_actions", []):
        next_steps.append(f"- {item.get('label')}: {item.get('reason')}")
    sections.append("\n".join(next_steps) or "- Configure a provider connection to enable model-backed synthesis.")
    return "\n".join(sections).strip()


def _extract_repo_copilot_sections(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    if not content.strip():
        return sections

    pattern = re.compile(
        r"^(## Intent / plan|## What ran|## What was found|## Recommended next step)\s*$",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(content))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections[match.group(1)] = content[start:end].strip()
    return sections


def _strip_repo_copilot_headings(content: str) -> str:
    stripped = content
    for heading in REPO_COPILOT_HEADINGS:
        stripped = stripped.replace(heading, "")
    return stripped.strip()


def _coerce_bullets(value: str) -> str:
    cleaned = _shorten(value, limit=1200)
    if not cleaned:
        return ""

    bullet_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("-", "*")):
            bullet_lines.append(line if line.startswith("- ") else f"- {line.lstrip('-* ').strip()}")
        else:
            bullet_lines.append(f"- {line}")
    return "\n".join(bullet_lines)


def normalize_repo_copilot_response(content: str, trace: dict[str, Any] | None) -> str:
    trace = trace or {}
    fallback_sections = _extract_repo_copilot_sections(build_repo_copilot_fallback_response(trace))
    parsed_sections = _extract_repo_copilot_sections(content)
    loose_model_summary = _coerce_bullets(_strip_repo_copilot_headings(content))

    normalized_sections: list[str] = []
    for heading in REPO_COPILOT_HEADINGS:
        body = (parsed_sections.get(heading) or "").strip()
        if not body:
            body = fallback_sections.get(heading, "").strip()

        if heading == "## What was found" and trace.get("failure_summary"):
            failure_summary = str(trace.get("failure_summary"))
            failure_label = FAILURE_CLASSIFICATION_LABELS.get(
                str(trace.get("failure_classification") or ""),
                str(trace.get("failure_classification") or "Unknown"),
            )
            primary_failure_target = str(trace.get("primary_failure_target") or "").strip()
            stderr_highlights = [str(item) for item in (trace.get("stderr_highlights") or []) if str(item).strip()]
            grounded_reasoning = [
                str(item) for item in (trace.get("grounded_next_step_reasoning") or []) if str(item).strip()
            ]
            failure_lines = [
                f"- Failure summary: {failure_summary}",
                f"- Failure type: {failure_label}",
            ]
            if primary_failure_target:
                failure_lines.append(f"- Fix this first: {primary_failure_target}")
            failure_lines.extend(f"- Stderr highlight: {item}" for item in stderr_highlights[:3])
            failure_lines.extend(f"- Why this likely failed: {item}" for item in grounded_reasoning[:3])
            failure_block = "\n".join(failure_lines)
            if failure_summary.lower() not in body.lower():
                body = f"{failure_block}\n{body}".strip()

        if heading == "## What was found" and loose_model_summary:
            evidence_already_present = loose_model_summary in body
            if not evidence_already_present:
                prefix = "\n" if body else ""
                body = f"{body}{prefix}- Model synthesis:\n{loose_model_summary}".strip()

        normalized_sections.append(heading)
        normalized_sections.append(body or fallback_sections.get(heading, "- No grounded evidence was collected."))
        normalized_sections.append("")

    return "\n".join(normalized_sections).strip()


async def _run_cli_probe(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation,
    parent_execution: RuntimeExecution,
    mode: ChatMode,
    title: str,
    summary: str,
    command: str,
    working_directory: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    step: dict[str, Any] = {
        "kind": "cli",
        "title": title,
        "summary": summary,
        "status": "queued",
        "command_preview": command,
        "is_read_only": True,
    }

    child_execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="chat_cli",
        provider_id=conversation.provider_id,
        model_id=conversation.model_id,
        provider_connection_id=conversation.provider_connection_id,
        resolved_model_name=conversation.model_name,
        conversation_id=conversation.id,
        prompt_preview=parent_execution.prompt_preview,
        command_preview=command[:4000],
        details_json={
            "copilot_step_title": title,
            "parent_execution_id": parent_execution.id,
            "execution_bundle_id": parent_execution.id,
            "mode": mode,
        },
    )
    step["runtime_execution_id"] = child_execution.id

    ephemeral_skill = SkillDefinition(
        id=f"chat-cli-{child_execution.id}",
        workspace_id=workspace.id,
        name=title,
        slug=f"chat-cli-{child_execution.id}",
        description=summary,
        prompt_template="",
        skill_mode="cli",
        required_runtime_type="cli",
        session_mode="reuse",
        working_directory=working_directory or ".",
        enabled=True,
    )

    try:
        await mark_runtime_running(session, child_execution)
        result = await dispatch_cli_execution(
            session,
            workspace=workspace,
            user=user,
            execution=child_execution,
            skill=ephemeral_skill,
            command=command,
            working_directory=working_directory or ".",
        )
        stdout = _shorten(result.get("stdout"))
        stderr = _shorten(result.get("stderr"))
        exit_code = int(result.get("exit_code") or 0)
        combined_excerpt = stdout or stderr or "Command returned no output."
        step.update(
            {
                "status": "succeeded" if exit_code == 0 else "failed",
                "output_excerpt": combined_excerpt,
                "stdout_excerpt": stdout or None,
                "stderr_excerpt": stderr or None,
                "exit_code": exit_code,
                "runtime_session_id": result.get("runtime_session_id"),
                "cwd": result.get("cwd"),
            }
        )
        evidence = {
            "title": title,
            "type": "command_output",
            "runtime_execution_id": child_execution.id,
            "content": combined_excerpt,
            "command_preview": command,
            "exit_code": exit_code,
            "stderr_excerpt": stderr or None,
            "path": result.get("cwd"),
        }
        details = {
            "copilot_step_title": title,
            "copilot_output_excerpt": combined_excerpt,
            "copilot_exit_code": exit_code,
            "stderr": stderr,
            "stdout": stdout,
            "cwd": result.get("cwd"),
            "parent_execution_id": parent_execution.id,
            "execution_bundle_id": parent_execution.id,
            "mode": mode,
        }
        if exit_code == 0:
            await mark_runtime_succeeded(
                session,
                child_execution,
                response_preview=combined_excerpt[:2000],
                details_json=details,
                artifacts_json=result.get("artifacts_json"),
            )
        else:
            await mark_runtime_failed(
                session,
                child_execution,
                error_message=(stderr or stdout or "CLI command failed"),
                details_json=details,
                artifacts_json=result.get("artifacts_json"),
            )
        return step, evidence
    except Exception as exc:
        step.update(
            {
                "status": "failed",
                "output_excerpt": str(exc),
                "stderr_excerpt": str(exc),
                "exit_code": -1,
            }
        )
        await mark_runtime_failed(
            session,
            child_execution,
            error_message=str(exc),
            details_json={
                "copilot_step_title": title,
                "parent_execution_id": parent_execution.id,
                "execution_bundle_id": parent_execution.id,
                "mode": mode,
            },
        )
        return step, {
            "title": title,
            "type": "command_output",
            "runtime_execution_id": child_execution.id,
            "content": str(exc),
            "command_preview": command,
        }


async def _run_browser_probe(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation,
    parent_execution: RuntimeExecution,
    mode: ChatMode,
    title: str,
    summary: str,
    actions: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    step: dict[str, Any] = {
        "kind": "browser",
        "title": title,
        "summary": summary,
        "status": "queued",
        "command_preview": actions,
        "is_read_only": True,
    }

    child_execution = await create_runtime_execution(
        session,
        workspace_id=workspace.id,
        user_id=user.id,
        source="chat",
        execution_kind="chat_browser",
        provider_id=conversation.provider_id,
        model_id=conversation.model_id,
        provider_connection_id=conversation.provider_connection_id,
        resolved_model_name=conversation.model_name,
        conversation_id=conversation.id,
        prompt_preview=parent_execution.prompt_preview,
        command_preview=str(actions)[:4000],
        details_json={
            "copilot_step_title": title,
            "parent_execution_id": parent_execution.id,
            "execution_bundle_id": parent_execution.id,
            "mode": mode,
        },
    )
    step["runtime_execution_id"] = child_execution.id

    ephemeral_skill = SkillDefinition(
        id=f"chat-browser-{child_execution.id}",
        workspace_id=workspace.id,
        name=title,
        slug=f"chat-browser-{child_execution.id}",
        description=summary,
        prompt_template="",
        skill_mode="browser",
        required_runtime_type="browser",
        session_mode="reuse",
        enabled=True,
    )

    try:
        await mark_runtime_running(session, child_execution)
        result = await dispatch_browser_execution(
            session,
            workspace=workspace,
            user=user,
            execution=child_execution,
            skill=ephemeral_skill,
            actions=actions,
        )
        extracted_text = _shorten(result.get("extracted_text"))
        artifact_summaries = summarize_artifacts(result.get("artifacts_json"))
        step.update(
            {
                "status": "succeeded",
                "output_excerpt": extracted_text or "Browser capture completed.",
                "runtime_session_id": result.get("runtime_session_id"),
                "artifact_summaries": artifact_summaries,
                "current_url": result.get("current_url"),
                "stdout_excerpt": extracted_text or None,
            }
        )
        evidence = {
            "title": title,
            "type": "browser_capture",
            "runtime_execution_id": child_execution.id,
            "content": extracted_text or (result.get("title") or result.get("current_url") or "Browser capture completed."),
            "artifact_summaries": artifact_summaries,
            "current_url": result.get("current_url"),
            "metadata": {"title": result.get("title")},
        }
        await mark_runtime_succeeded(
            session,
            child_execution,
            response_preview=(extracted_text or result.get("title") or result.get("current_url") or "Browser capture completed.")[:2000],
            details_json={
                "copilot_step_title": title,
                "current_url": result.get("current_url"),
                "title": result.get("title"),
                "extracted_text": extracted_text,
                "parent_execution_id": parent_execution.id,
                "execution_bundle_id": parent_execution.id,
                "mode": mode,
            },
            artifacts_json=result.get("artifacts_json"),
        )
        return step, evidence
    except Exception as exc:
        failed_url: str | None = None
        if actions:
            first_action = actions[0]
            url_candidate = first_action.get("url")
            if isinstance(url_candidate, str) and url_candidate:
                failed_url = url_candidate
        step.update(
            {
                "status": "failed",
                "output_excerpt": str(exc),
                "stderr_excerpt": str(exc),
                "exit_code": -1,
                "current_url": failed_url,
            }
        )
        await mark_runtime_failed(
            session,
            child_execution,
            error_message=str(exc),
            details_json={
                "copilot_step_title": title,
                "parent_execution_id": parent_execution.id,
                "execution_bundle_id": parent_execution.id,
                "mode": mode,
            },
        )
        return step, {
            "title": title,
            "type": "browser_capture",
            "runtime_execution_id": child_execution.id,
            "content": str(exc),
            "metadata": {"actions": actions},
        }


def build_planned_actions(planned_steps: list[PlannedStep]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for index, planned_step in enumerate(planned_steps, start=1):
        payload_preview: dict[str, Any] | str | None = None
        target_label = planned_step.working_directory
        if planned_step.kind == "cli":
            payload_preview = planned_step.command
            target_label = planned_step.command
        elif planned_step.kind == "browser":
            payload_preview = {"actions": planned_step.actions or []}
            if planned_step.actions:
                first_action = planned_step.actions[0]
                target_label = str(first_action.get("url") or first_action.get("action") or planned_step.title)

        actions.append(
            build_annotation(
                annotation_id=f"planned-{index}",
                kind="plan_generated",
                title=planned_step.title,
                summary=planned_step.summary,
                status="ready",
                source_layer="chat",
                payload_preview=payload_preview,
                target_label=target_label,
            )
        )
    return actions


def build_actual_timeline(
    *,
    doctor_result: dict[str, Any],
    trace_steps: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    knowledge_sources: list[KnowledgeChunkReference] | None,
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = [
        build_annotation(
            annotation_id="doctor-check",
            kind="doctor_checked",
            title="Environment doctor",
            summary=_doctor_summary_label(doctor_result),
            status=str((doctor_result.get("workspace") or {}).get("status") or "ready"),
            source_layer="chat",
            payload_preview={
                "machine_status": (doctor_result.get("machine_summary") or {}).get("status"),
                "workspace_status": (doctor_result.get("workspace") or {}).get("status"),
            },
        )
    ]

    if knowledge_sources:
        timeline.append(
            build_annotation(
                annotation_id="knowledge-context",
                kind="knowledge_retrieved",
                title="Knowledge context loaded",
                summary=f"Attached {len(knowledge_sources)} knowledge snippets to ground the repo copilot pass.",
                status="succeeded",
                source_layer="knowledge",
                evidence_refs=[
                    {"document_id": item.document_id, "document_name": item.document_name, "chunk_id": item.chunk_id}
                    for item in knowledge_sources[:4]
                ],
                payload_preview={"documents": [item.document_name for item in knowledge_sources[:4]]},
            )
        )

    for index, step in enumerate(trace_steps[1:], start=1):
        step_kind = str(step.get("kind") or "runtime")
        step_status = str(step.get("status") or "succeeded")
        annotation_kind = {
            "cli": "command_finished",
            "browser": "browser_action",
            "doctor": "doctor_checked",
        }.get(step_kind, "repo_scanned")
        payload_preview: dict[str, Any] | str | None = step.get("command_preview")
        if step_kind == "browser":
            payload_preview = {
                "actions": step.get("command_preview"),
                "current_url": step.get("current_url"),
            }
        timeline.append(
            build_annotation(
                annotation_id=f"step-{index}",
                kind=annotation_kind,
                title=str(step.get("title") or "Execution step"),
                summary=str(step.get("summary") or ""),
                status=_timeline_status(step_status),
                source_layer="runtime",
                runtime_execution_id=step.get("runtime_execution_id"),
                runtime_session_id=step.get("runtime_session_id"),
                evidence_refs=[{"runtime_execution_id": step.get("runtime_execution_id")}]
                if step.get("runtime_execution_id")
                else [],
                payload_preview=payload_preview,
                raw_payload=step,
                target_label=str(step.get("current_url") or step.get("command_preview") or step.get("title") or ""),
            )
        )
        if step.get("artifact_summaries"):
            timeline.append(
                build_annotation(
                    annotation_id=f"artifact-{index}",
                    kind="artifact_captured",
                    title=f"{step.get('title')} artifacts",
                    summary="Captured artifacts from the runtime step for later inspection.",
                    status="succeeded",
                    source_layer="runtime",
                    runtime_execution_id=step.get("runtime_execution_id"),
                    runtime_session_id=step.get("runtime_session_id"),
                    payload_preview={"artifacts": step.get("artifact_summaries")},
                    raw_payload={"artifact_summaries": step.get("artifact_summaries")},
                )
            )

    if evidence:
        timeline.append(
            build_annotation(
                annotation_id="message-compose",
                kind="message_composed",
                title="Answer composed",
                summary="Compiled execution evidence into a grounded repo copilot response.",
                status="succeeded",
                source_layer="chat",
                payload_preview={"evidence_count": len(evidence)},
            )
        )

    return timeline


async def collect_repo_copilot_trace(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    conversation: Conversation,
    parent_execution: RuntimeExecution,
    prompt: str,
    mode: ChatMode | None = None,
    knowledge_sources: list[KnowledgeChunkReference] | None = None,
) -> dict[str, Any]:
    scenario_tag, router_reason, resolved_mode = classify_repo_copilot_scenario(prompt, mode)
    search_term = extract_search_term(prompt)
    browser_url = extract_target_url(prompt)
    runtimes = await list_runtimes_for_workspace(session, workspace.id)
    doctor_result = build_doctor_result(workspace=workspace, runtimes=runtimes, default_workspace_id=workspace.id)

    trace_steps: list[dict[str, Any]] = [
        {
            "kind": "doctor",
            "title": "Environment doctor",
            "summary": _doctor_summary_label(doctor_result),
            "status": (doctor_result.get("workspace") or {}).get("status") or "ready",
            "is_read_only": True,
        }
    ]
    evidence: list[dict[str, Any]] = [
        {
            "title": "Environment doctor",
            "type": "doctor",
            "content": _doctor_summary_label(doctor_result),
            "metadata": {
                "machine_status": (doctor_result.get("machine_summary") or {}).get("status"),
                "workspace_status": (doctor_result.get("workspace") or {}).get("status"),
            },
        }
    ]

    if knowledge_sources:
        evidence.append(
            {
                "title": "Knowledge context",
                "type": "knowledge",
                "content": ", ".join(source.document_name for source in knowledge_sources[:4]),
                "source_names": [source.document_name for source in knowledge_sources[:4]],
            }
        )

    planned_steps = build_planned_steps(
        scenario_tag,
        prompt=prompt,
        search_term=search_term,
        browser_url=browser_url,
    )
    planned_actions = build_planned_actions(planned_steps)

    for planned_step in planned_steps:
        if planned_step.kind == "cli":
            step, evidence_item = await _run_cli_probe(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=parent_execution,
                mode=resolved_mode,
                title=planned_step.title,
                summary=planned_step.summary,
                command=planned_step.command or "",
                working_directory=planned_step.working_directory,
            )
            trace_steps.append(step)
            evidence.append(evidence_item)
        elif planned_step.kind == "browser":
            step, evidence_item = await _run_browser_probe(
                session,
                workspace=workspace,
                user=user,
                conversation=conversation,
                parent_execution=parent_execution,
                mode=resolved_mode,
                title=planned_step.title,
                summary=planned_step.summary,
                actions=planned_step.actions or [],
            )
            trace_steps.append(step)
            evidence.append(evidence_item)

    failure_state = analyze_failure_state(
        doctor_result=doctor_result,
        trace_steps=trace_steps,
    )

    recommended_next_actions = build_recommended_next_actions(
        scenario_tag,
        doctor_result=doctor_result,
        trace_steps=trace_steps,
        search_term=search_term,
        failure_state=failure_state,
    )
    proposal = build_proposal(
        mode=resolved_mode,
        scenario_tag=scenario_tag,
        search_term=search_term,
        trace_steps=trace_steps,
        evidence=evidence,
        failure_state=failure_state,
    )

    runtime_execution_ids = [step.get("runtime_execution_id") for step in trace_steps if step.get("runtime_execution_id")]
    child_execution_ids = list(runtime_execution_ids)
    artifact_summaries = [
        artifact
        for step in trace_steps
        for artifact in (step.get("artifact_summaries") or [])
    ]
    actual_events = build_actual_timeline(
        doctor_result=doctor_result,
        trace_steps=trace_steps,
        evidence=evidence,
        knowledge_sources=knowledge_sources,
    )
    next_action_events = [
        build_annotation(
            annotation_id=f"next-{index}",
            kind="next_action_suggested",
            title=item.get("label"),
            summary=item.get("reason") or "",
            status="ready",
            source_layer="chat",
        )
        for index, item in enumerate(recommended_next_actions, start=1)
    ]
    proposal_events = []
    if proposal:
        proposal_events.append(
            build_annotation(
                annotation_id="proposal-generated",
                kind="next_action_suggested",
                title="Proposal generated",
                summary=str(proposal.get("summary") or "Generated a proposal-only repair path."),
                status="ready",
                source_layer="chat",
                payload_preview={
                    "targets": proposal.get("targets"),
                    "suggested_commands": proposal.get("suggested_commands"),
                },
            )
        )
    timeline = [*planned_actions, *actual_events, *proposal_events, *next_action_events]

    status = "failed" if any(step.get("status") == "failed" for step in trace_steps) else "succeeded"

    return {
        "mode": resolved_mode,
        "mode_summary": {
            "active_mode": resolved_mode,
            "requested_mode": mode,
            "inferred_from": "user_selection" if mode else "auto_router",
            "rationale": router_reason,
        },
        "scenario_tag": scenario_tag,
        "scenario_label": SCENARIO_LABELS[scenario_tag],
        "router_reason": router_reason,
        "intent_plan": build_intent_plan(
            scenario_tag,
            mode=resolved_mode,
            search_term=search_term,
            browser_url=browser_url,
        ),
        "steps": trace_steps,
        "evidence": evidence,
        "evidence_items": evidence,
        "execution_bundle_id": parent_execution.id,
        "child_execution_ids": child_execution_ids,
        "machine_summary": doctor_result.get("machine_summary"),
        "workspace_readiness": doctor_result.get("workspace"),
        "install_guidance": doctor_result.get("install_guidance") or [],
        "recommended_next_actions": recommended_next_actions,
        "runtime_execution_ids": runtime_execution_ids,
        "artifact_summaries": artifact_summaries,
        "primary_failure_target": failure_state.get("primary_failure_target") if failure_state else None,
        "failure_summary": failure_state.get("failure_summary") if failure_state else None,
        "failure_classification": failure_state.get("failure_classification") if failure_state else None,
        "stderr_highlights": list(failure_state.get("stderr_highlights") or []) if failure_state else [],
        "grounded_next_step_reasoning": list(failure_state.get("grounded_next_step_reasoning") or []) if failure_state else [],
        "planned_actions": planned_actions,
        "actual_events": actual_events,
        "timeline": timeline,
        "proposal": proposal,
        "trace_summary": {
            "headline": f"{MODE_LABELS[resolved_mode]} / {SCENARIO_LABELS[scenario_tag]}",
            "summary": router_reason,
            "status": status,
            "timeline_count": len(timeline),
            "has_artifacts": bool(artifact_summaries),
        },
        "safety_summary": {
            "mode": "read_only_auto_execute",
            "blocked_write_actions": True,
            "proposal_only": resolved_mode == "propose_fix",
        },
    }
