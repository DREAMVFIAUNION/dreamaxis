from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from app.models.runtime_host import RuntimeHost
from app.models.skill_definition import SkillDefinition
from app.models.workspace import Workspace
from app.schemas.environment import (
    DoctorCheckResult,
    EnvironmentCapability,
    EnvironmentProfile,
    EnvironmentSummary,
    RuntimeDoctorSnapshot,
    SkillCompatibilityStatus,
    WorkspaceEnvironmentStatus,
)

REQUIRED_MACHINE_CAPABILITIES = ["git", "node", "package_manager", "python"]
OPTIONAL_MACHINE_CAPABILITIES = ["docker", "browser_runtime", "playwright", "shell_profile"]
WORKSPACE_CAPABILITIES = ["safe_root", "workspace_repo", "node_project", "python_project", "docker_project"]

CAPABILITY_TITLES = {
    "git": "Git",
    "node": "Node.js",
    "package_manager": "Package manager",
    "python": "Python",
    "docker": "Docker",
    "browser_runtime": "Browser runtime",
    "playwright": "Playwright",
    "shell_profile": "Shell profile",
    "safe_root": "Workspace root",
    "workspace_repo": "Git repository",
    "node_project": "Node.js project",
    "python_project": "Python project",
    "docker_project": "Docker project",
}

INSTALL_HINTS = {
    "git": "Install Git and ensure `git --version` works in your shell.",
    "node": "Install Node.js LTS and re-open the terminal so `node --version` is available.",
    "package_manager": "Install pnpm or keep npm available; DreamAxis expects one package manager in PATH.",
    "python": "Install Python 3.12+ and ensure `python --version` works in PATH.",
    "docker": "Install Docker Desktop if you want container-aware CLI skills and compose workflows.",
    "browser_runtime": "Enable the Browser Runtime service and confirm the browser worker can start successfully.",
    "playwright": "Run `playwright install chromium` (or re-build the browser worker image) to install browser binaries.",
    "shell_profile": "Install PowerShell/pwsh or configure DreamAxis to use an available shell.",
    "safe_root": "Point the workspace to a valid local directory before running CLI or repo skills.",
    "workspace_repo": "Open or bind a Git repository workspace so repo-aware skills can inspect it safely.",
    "node_project": "Add or select a workspace with a `package.json` when using Node-focused skills.",
    "python_project": "Add or select a workspace with `pyproject.toml`, `requirements.txt`, or `setup.py` for Python-focused skills.",
    "docker_project": "Add a `Dockerfile` or `docker-compose.yml` if you want Docker project automation in this workspace.",
}


def environment_profile() -> EnvironmentProfile:
    return EnvironmentProfile(
        slug="desktop-standard-v1",
        name="DreamAxis Desktop Standard v1",
        required_capabilities=list(REQUIRED_MACHINE_CAPABILITIES),
        optional_capabilities=list(OPTIONAL_MACHINE_CAPABILITIES),
        workspace_capabilities=list(WORKSPACE_CAPABILITIES),
        default_shell="powershell",
    )


def _capability_status(*, installed: bool, required: bool) -> str:
    if installed:
        return "ready"
    return "missing" if required else "degraded"


def _make_capability(
    name: str,
    *,
    installed: bool,
    required: bool,
    version: str | None = None,
    source: str = "runtime",
    message: str | None = None,
    install_hint: str | None = None,
) -> dict[str, Any]:
    return EnvironmentCapability(
        name=name,
        installed=installed,
        version=version,
        required=required,
        status=_capability_status(installed=installed, required=required),
        source=source,
        message=message,
        install_hint=install_hint or INSTALL_HINTS.get(name),
    ).model_dump()


def summarize_capabilities(capabilities: Iterable[dict[str, Any]]) -> dict[str, Any]:
    normalized = list(capabilities)
    counts = Counter(item.get("status") or "degraded" for item in normalized)
    missing_required = [
        item["name"]
        for item in normalized
        if item.get("required") and not item.get("installed")
    ]
    warnings = [
        item["name"]
        for item in normalized
        if item.get("status") == "degraded" and not item.get("installed")
    ]
    if missing_required:
        status = "missing"
    elif warnings:
        status = "degraded"
    else:
        status = "ready"
    return EnvironmentSummary(
        status=status,
        ready_count=counts.get("ready", 0),
        degraded_count=counts.get("degraded", 0),
        missing_count=counts.get("missing", 0),
        missing_required=missing_required,
        warnings=warnings,
    ).model_dump()


def extract_environment_snapshot(runtime: RuntimeHost) -> dict[str, Any]:
    capabilities = runtime.capabilities_json or {}
    environment = capabilities.get("environment")
    return environment if isinstance(environment, dict) else {}


def _merge_capabilities(
    snapshots: Iterable[dict[str, Any]],
    names: list[str],
    *,
    required_names: set[str],
    section: str,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for snapshot in snapshots:
        entries = (((snapshot.get(section) or {}).get("capabilities")) or [])
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            current = merged.get(name)
            installed = bool(entry.get("installed"))
            if current is None or (installed and not current.get("installed")):
                merged[name] = {
                    "name": name,
                    "installed": installed,
                    "version": entry.get("version"),
                    "required": name in required_names,
                    "status": entry.get("status") or _capability_status(installed=installed, required=name in required_names),
                    "source": entry.get("source") or "runtime",
                    "message": entry.get("message"),
                    "install_hint": entry.get("install_hint") or INSTALL_HINTS.get(name),
                }

    ordered: list[dict[str, Any]] = []
    for name in names:
        if name in merged:
            merged[name]["required"] = name in required_names
            if not merged[name].get("status"):
                merged[name]["status"] = _capability_status(
                    installed=bool(merged[name].get("installed")),
                    required=name in required_names,
                )
            ordered.append(merged[name])
        else:
            ordered.append(
                _make_capability(
                    name,
                    installed=False,
                    required=name in required_names,
                    source="doctor",
                    message=f"{CAPABILITY_TITLES.get(name, name)} has not been detected yet.",
                )
            )

    extra = sorted(name for name in merged if name not in names)
    ordered.extend(merged[name] for name in extra)
    return ordered


def build_machine_capabilities(runtimes: list[RuntimeHost]) -> list[dict[str, Any]]:
    snapshots = [extract_environment_snapshot(runtime) for runtime in runtimes]
    ordered_names = REQUIRED_MACHINE_CAPABILITIES + OPTIONAL_MACHINE_CAPABILITIES
    return _merge_capabilities(
        snapshots,
        ordered_names,
        required_names=set(REQUIRED_MACHINE_CAPABILITIES),
        section="machine",
    )


def build_workspace_readiness(workspace: Workspace, runtimes: list[RuntimeHost]) -> dict[str, Any]:
    snapshots = [extract_environment_snapshot(runtime) for runtime in runtimes]
    capabilities = _merge_capabilities(
        snapshots,
        WORKSPACE_CAPABILITIES,
        required_names=set(),
        section="workspace",
    )
    root_path = None
    for snapshot in snapshots:
        workspace_snapshot = snapshot.get("workspace") or {}
        if isinstance(workspace_snapshot, dict) and workspace_snapshot.get("root_path"):
            root_path = workspace_snapshot["root_path"]
            break
    summary = summarize_capabilities(capabilities)
    return WorkspaceEnvironmentStatus(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        root_path=root_path or workspace.workspace_root_path,
        status=summary["status"],
        capabilities=[EnvironmentCapability.model_validate(item) for item in capabilities],
        summary=EnvironmentSummary.model_validate(summary),
    ).model_dump()


def list_install_guidance(*capabilities_sets: Iterable[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    guidance: list[str] = []
    for capabilities in capabilities_sets:
        for capability in capabilities:
            if capability.get("installed"):
                continue
            hint = capability.get("install_hint")
            if hint and hint not in seen:
                seen.add(hint)
                guidance.append(hint)
    return guidance


def build_runtime_snapshots(runtimes: list[RuntimeHost]) -> list[dict[str, Any]]:
    snapshots = []
    for runtime in runtimes:
        snapshots.append(
            RuntimeDoctorSnapshot(
                runtime_id=runtime.id,
                runtime_name=runtime.name,
                runtime_type=runtime.runtime_type,
                status=runtime.status,
                doctor_status=runtime.doctor_status,
                last_capability_check_at=runtime.last_capability_check_at,
            ).model_dump()
        )
    return snapshots


def evaluate_skill_compatibility(
    skill: SkillDefinition,
    *,
    machine_capabilities: Iterable[dict[str, Any]],
    workspace_capabilities: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    machine_index = {item["name"]: item for item in machine_capabilities}
    workspace_index = {item["name"]: item for item in workspace_capabilities}

    required = list(skill.required_capabilities or [])
    recommended = list(skill.recommended_capabilities or [])
    workspace_requirements = list(skill.workspace_requirements or [])

    if skill.skill_mode == "cli":
        if "python" not in required:
            required.append("python")
        if "safe_root" not in workspace_requirements:
            workspace_requirements.append("safe_root")
    if skill.skill_mode == "browser" and "browser_runtime" not in required:
        required.append("browser_runtime")

    missing_required = [name for name in required if not machine_index.get(name, {}).get("installed")]
    missing_workspace = [name for name in workspace_requirements if not workspace_index.get(name, {}).get("installed")]
    missing_recommended = [name for name in recommended if not machine_index.get(name, {}).get("installed")]

    if missing_required or missing_workspace:
        status = "blocked"
        message = "Missing required environment capabilities."
    elif missing_recommended:
        status = "warn"
        message = "Skill can run, but optional environment capabilities are missing."
    else:
        status = "ready"
        message = "Skill is compatible with the current local environment."

    return SkillCompatibilityStatus(
        status=status,
        message=message,
        missing_required_capabilities=missing_required,
        missing_workspace_requirements=missing_workspace,
        missing_recommended_capabilities=missing_recommended,
    ).model_dump()


def summarize_skill_compatibility(
    skills: Iterable[SkillDefinition],
    *,
    machine_capabilities: Iterable[dict[str, Any]],
    workspace_capabilities: Iterable[dict[str, Any]],
) -> dict[str, int]:
    counts = Counter()
    for skill in skills:
        compatibility = evaluate_skill_compatibility(
            skill,
            machine_capabilities=machine_capabilities,
            workspace_capabilities=workspace_capabilities,
        )
        counts[compatibility["status"]] += 1
    return {
        "ready": counts.get("ready", 0),
        "warn": counts.get("warn", 0),
        "blocked": counts.get("blocked", 0),
        "total": sum(counts.values()),
    }


def build_doctor_result(
    *,
    workspace: Workspace,
    runtimes: list[RuntimeHost],
    skills: Iterable[SkillDefinition] = (),
    default_workspace_id: str | None = None,
) -> dict[str, Any]:
    machine_capabilities = build_machine_capabilities(runtimes)
    machine_summary = summarize_capabilities(machine_capabilities)
    workspace_status = build_workspace_readiness(workspace, runtimes)
    workspace_capabilities = [item.model_dump() if hasattr(item, "model_dump") else item for item in workspace_status["capabilities"]]
    skill_compatibility = summarize_skill_compatibility(
        skills,
        machine_capabilities=machine_capabilities,
        workspace_capabilities=workspace_capabilities,
    )
    return DoctorCheckResult(
        profile=environment_profile(),
        default_workspace_id=default_workspace_id,
        machine_capabilities=[EnvironmentCapability.model_validate(item) for item in machine_capabilities],
        machine_summary=EnvironmentSummary.model_validate(machine_summary),
        workspace=WorkspaceEnvironmentStatus.model_validate(workspace_status),
        runtimes=[RuntimeDoctorSnapshot.model_validate(item) for item in build_runtime_snapshots(runtimes)],
        install_guidance=list_install_guidance(machine_capabilities, workspace_capabilities),
        skill_compatibility=skill_compatibility,
    ).model_dump()
