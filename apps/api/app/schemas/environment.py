from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EnvironmentCapability(BaseModel):
    name: str
    installed: bool
    version: str | None = None
    required: bool = False
    status: str
    source: str
    message: str | None = None
    install_hint: str | None = None


class EnvironmentSummary(BaseModel):
    status: str
    ready_count: int = 0
    degraded_count: int = 0
    missing_count: int = 0
    missing_required: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EnvironmentProfile(BaseModel):
    slug: str
    name: str
    required_capabilities: list[str] = Field(default_factory=list)
    optional_capabilities: list[str] = Field(default_factory=list)
    workspace_capabilities: list[str] = Field(default_factory=list)
    default_shell: str | None = None


class WorkspaceEnvironmentStatus(BaseModel):
    workspace_id: str
    workspace_name: str
    root_path: str | None = None
    status: str
    capabilities: list[EnvironmentCapability] = Field(default_factory=list)
    summary: EnvironmentSummary


class CapabilityRequirement(BaseModel):
    name: str
    scope: str = "machine"
    required: bool = True
    reason: str | None = None


class SkillCompatibilityStatus(BaseModel):
    status: str
    message: str | None = None
    missing_required_capabilities: list[str] = Field(default_factory=list)
    missing_workspace_requirements: list[str] = Field(default_factory=list)
    missing_recommended_capabilities: list[str] = Field(default_factory=list)


class RuntimeDoctorSnapshot(BaseModel):
    runtime_id: str
    runtime_name: str
    runtime_type: str
    status: str
    doctor_status: str | None = None
    last_capability_check_at: datetime | None = None


class DoctorCheckResult(BaseModel):
    profile: EnvironmentProfile
    default_workspace_id: str | None = None
    machine_capabilities: list[EnvironmentCapability] = Field(default_factory=list)
    machine_summary: EnvironmentSummary
    workspace: WorkspaceEnvironmentStatus | None = None
    runtimes: list[RuntimeDoctorSnapshot] = Field(default_factory=list)
    install_guidance: list[str] = Field(default_factory=list)
    skill_compatibility: dict[str, int] = Field(default_factory=dict)


class EnvironmentOverview(BaseModel):
    profile: EnvironmentProfile
    default_workspace_id: str | None = None
    runtime_types: list[str] = Field(default_factory=list)
    runtimes: list[RuntimeDoctorSnapshot] = Field(default_factory=list)
