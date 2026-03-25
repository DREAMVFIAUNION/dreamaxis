from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DesktopContextSnapshot(BaseModel):
    system_info: dict[str, str]
    process_list: list[str]
    top_level_windows: list[str]
    foreground_window: str | None = None
    screenshot_summary: str | None = None
    ocr_text: str | None = None
    ui_node_summary: str | None = None
    prompt_derived_target: str


class DesktopTargetResolverResult(BaseModel):
    resolved: bool
    target_type: Literal["app", "window", "ui_node", "ocr_match", "focused_fallback", "desktop"]
    target_identifier: str
    confidence: float
    resolver_path: list[str]
    failure_reason: str | None = None
    context_snapshot: DesktopContextSnapshot
