from __future__ import annotations

import base64
import csv
import ctypes
import io
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ctypes import wintypes

from fastapi import HTTPException
from PIL import ImageGrab

try:
    import pytesseract
except Exception:
    pytesseract = None


@dataclass
class DesktopSession:
    session_id: str
    workspace_id: str
    session_type: str
    reusable: bool
    context_json: dict[str, Any]
    status: str = "idle"


SESSIONS: dict[str, DesktopSession] = {}

SW_RESTORE = 9
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1
WINDOW_TARGET_ALIASES: dict[str, list[str]] = {
    "vs code": ["vs code", "visual studio code"],
    "visual studio code": ["visual studio code", "vs code"],
    "terminal": ["terminal", "windows terminal", "powershell", "command prompt", "pwsh"],
    "windows terminal": ["windows terminal", "terminal", "powershell", "pwsh"],
    "powershell": ["powershell", "windows powershell", "terminal", "pwsh"],
    "browser": ["browser", "chrome", "google chrome", "edge", "microsoft edge", "firefox"],
    "chrome": ["chrome", "google chrome", "browser"],
    "edge": ["edge", "microsoft edge", "browser"],
}
VK_CODES: dict[str, int] = {
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B,
    "windows": 0x5B,
    "enter": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
}
for digit in "0123456789":
    VK_CODES[digit] = ord(digit)
for letter in "abcdefghijklmnopqrstuvwxyz":
    VK_CODES[letter] = ord(letter.upper())
for index in range(1, 13):
    VK_CODES[f"f{index}"] = 0x6F + index


ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


def _is_windows_host() -> bool:
    return platform.system() == "Windows"


def _append_warning(warnings: list[str], message: str | None) -> None:
    if not message:
        return
    normalized = str(message).strip()
    if normalized and normalized not in warnings:
        warnings.append(normalized)


def _diagnostic_artifact(name: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "kind": "diagnostic",
        "name": name,
        "text": text,
        "metadata": metadata or {},
    }


def create_session(*, session_id: str, workspace_id: str, session_type: str, reusable: bool, context_json: dict[str, Any]) -> DesktopSession:
    session = DesktopSession(
        session_id=session_id,
        workspace_id=workspace_id,
        session_type=session_type,
        reusable=reusable,
        context_json=context_json,
    )
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> DesktopSession:
    session = SESSIONS.get(session_id)
    if not session or session.status == "closed":
        raise HTTPException(status_code=404, detail="Desktop session not found")
    return session


def close_session(session_id: str) -> None:
    session = get_session(session_id)
    session.status = "closed"


def _list_processes(limit: int = 80) -> tuple[list[dict[str, Any]], str | None]:
    if shutil.which("tasklist"):
        completed = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True, check=False)
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(csv.reader(io.StringIO(completed.stdout or ""))):
            if len(row) < 2:
                continue
            rows.append({"name": row[0], "pid": row[1], "session_name": row[2] if len(row) > 2 else None})
            if index + 1 >= limit:
                break
        return rows, None

    if shutil.which("ps"):
        completed = subprocess.run(["ps", "-eo", "pid=,comm="], capture_output=True, text=True, check=False)
        rows = []
        for index, raw_line in enumerate((completed.stdout or "").splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            rows.append({"pid": parts[0], "name": parts[1], "session_name": None})
            if index + 1 >= limit:
                break
        return rows, "Using a portable process-list fallback because Windows tasklist is unavailable in this runtime."

    return [], "Process listing is unavailable in the current desktop runtime environment."


def _enum_windows() -> tuple[list[dict[str, Any]], str | None]:
    if not _is_windows_host():
        return [], "Top-level window enumeration is only available on a native Windows desktop host."
    user32 = ctypes.windll.user32
    windows: list[dict[str, Any]] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def foreach_window(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append({"handle": int(hwnd), "title": title, "pid": int(pid.value)})
        return True

    user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
    return windows, None


def _foreground_window() -> tuple[dict[str, Any] | None, str | None]:
    if not _is_windows_host():
        return None, "Foreground window inspection is only available on a native Windows desktop host."
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None, None
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {"handle": int(hwnd), "title": buffer.value.strip() or "Unknown window", "pid": int(pid.value)}, None


def _candidate_window_terms(target: str) -> list[str]:
    lowered = target.strip().lower()
    if not lowered:
        return []
    terms: list[str] = []
    for item in WINDOW_TARGET_ALIASES.get(lowered, [lowered]):
        normalized = item.strip().lower()
        if normalized and normalized not in terms:
            terms.append(normalized)
    if lowered not in terms:
        terms.append(lowered)
    return terms


def _window_matches_target(window: dict[str, Any] | None, target: str | None) -> bool:
    if not window or not target:
        return False
    title = str(window.get("title") or "").strip().lower()
    if not title:
        return False
    return any(term in title for term in _candidate_window_terms(target))


def _match_window(target: str | None = None, handle: int | None = None) -> dict[str, Any]:
    windows, warning = _enum_windows()
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    if handle is not None:
        matched = next((item for item in windows if int(item.get("handle") or 0) == int(handle)), None)
        if matched:
            return matched
    if target:
        candidate_terms = _candidate_window_terms(target)
        exact = next(
            (
                item
                for item in windows
                if str(item.get("title") or "").strip().lower() in candidate_terms
            ),
            None,
        )
        if exact:
            return exact
        partial = next(
            (
                item
                for item in windows
                if any(term in str(item.get("title") or "").strip().lower() for term in candidate_terms)
            ),
            None,
        )
        if partial:
            return partial
        raise HTTPException(status_code=404, detail=f"Could not find a desktop window for explicit target: {target}")
    active, _ = _foreground_window()
    if active:
        return active
    raise HTTPException(status_code=404, detail=f"Could not find a desktop window for target: {target or handle or 'active'}")


def _focus_window(target: str | None = None, handle: int | None = None) -> dict[str, Any]:
    if not _is_windows_host():
        raise HTTPException(status_code=400, detail="Window focus is only available on a native Windows desktop host.")
    window = _match_window(target=target, handle=handle)
    hwnd = int(window["handle"])
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    active, _ = _foreground_window()
    return {
        "requested_target": target,
        "requested_handle": handle,
        "matched_window": window,
        "active_window": active,
        "focused": bool(active and int(active.get("handle") or 0) == hwnd),
    }


def _resolve_command(candidates: list[list[str]]) -> list[str] | None:
    for candidate in candidates:
        executable = candidate[0]
        if Path(executable).exists() or shutil.which(executable):
            return candidate
    return None


def _launch_app(target_app: str | None, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if not _is_windows_host():
        raise HTTPException(status_code=400, detail="App launch is only available on a native Windows desktop host.")
    if not target_app:
        raise HTTPException(status_code=400, detail="Desktop launch_app requires a target_app.")

    normalized = target_app.strip().lower()
    args = arguments or {}
    url = str(args.get("url") or "about:blank").strip()
    user_profile = Path.home()
    allowlist: dict[str, list[list[str]]] = {
        "visual studio code": [
            ["code"],
            [str(user_profile / "AppData/Local/Programs/Microsoft VS Code/Code.exe")],
            [r"C:\Program Files\Microsoft VS Code\Code.exe"],
        ],
        "vs code": [
            ["code"],
            [str(user_profile / "AppData/Local/Programs/Microsoft VS Code/Code.exe")],
            [r"C:\Program Files\Microsoft VS Code\Code.exe"],
        ],
        "vscode": [
            ["code"],
            [str(user_profile / "AppData/Local/Programs/Microsoft VS Code/Code.exe")],
            [r"C:\Program Files\Microsoft VS Code\Code.exe"],
        ],
        "terminal": [["wt"], ["powershell.exe"]],
        "windows terminal": [["wt"]],
        "powershell": [["powershell.exe"]],
        "browser": [["msedge", url], ["chrome", url], ["cmd", "/c", "start", "", url]],
        "edge": [["msedge", url]],
        "chrome": [["chrome", url]],
    }
    candidates = allowlist.get(normalized)
    if not candidates:
        raise HTTPException(status_code=400, detail=f"App is not allowlisted for desktop launch: {target_app}")
    command = _resolve_command(candidates)
    if not command:
        raise HTTPException(status_code=404, detail=f"Could not resolve an executable for allowlisted app: {target_app}")
    process = subprocess.Popen(command)
    return {
        "target_app": target_app,
        "command": command,
        "pid": process.pid,
    }


def _mouse_flags(button: str) -> tuple[int, int]:
    lowered = button.strip().lower()
    if lowered == "right":
        return MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    return MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP


def _click_at(x: int, y: int, *, button: str = "left", clicks: int = 1) -> dict[str, Any]:
    if not _is_windows_host():
        raise HTTPException(status_code=400, detail="Mouse click is only available on a native Windows desktop host.")
    user32 = ctypes.windll.user32
    screen_left = int(user32.GetSystemMetrics(76))
    screen_top = int(user32.GetSystemMetrics(77))
    screen_width = int(user32.GetSystemMetrics(78))
    screen_height = int(user32.GetSystemMetrics(79))
    screen_right = screen_left + screen_width
    screen_bottom = screen_top + screen_height
    if not (screen_left <= int(x) < screen_right and screen_top <= int(y) < screen_bottom):
        raise HTTPException(
            status_code=400,
            detail=(
                "Click target is outside the current virtual screen bounds: "
                f"({screen_left},{screen_top}) to ({screen_right - 1},{screen_bottom - 1})."
            ),
        )
    down_flag, up_flag = _mouse_flags(button)
    user32.SetCursorPos(int(x), int(y))
    for _ in range(max(1, int(clicks))):
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        time.sleep(0.05)
    return {
        "x": int(x),
        "y": int(y),
        "button": button,
        "clicks": int(clicks),
        "virtual_screen_bounds": {
            "left": screen_left,
            "top": screen_top,
            "right": screen_right,
            "bottom": screen_bottom,
            "width": screen_width,
            "height": screen_height,
        },
    }


def _send_unicode_text(text: str) -> int:
    if not _is_windows_host():
        raise HTTPException(status_code=400, detail="Text input is only available on a native Windows desktop host.")
    if not text:
        return 0

    user32 = ctypes.windll.user32
    events_sent = 0
    for char in text:
        vk_combo = user32.VkKeyScanW(ord(char))
        if vk_combo != -1:
            vk = vk_combo & 0xFF
            shift_state = (vk_combo >> 8) & 0xFF
            modifiers: list[int] = []
            if shift_state & 1:
                modifiers.append(VK_CODES["shift"])
            if shift_state & 2:
                modifiers.append(VK_CODES["ctrl"])
            if shift_state & 4:
                modifiers.append(VK_CODES["alt"])
            for modifier in modifiers:
                user32.keybd_event(modifier, 0, 0, 0)
                events_sent += 1
                time.sleep(0.01)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            events_sent += 2
            time.sleep(0.01)
            for modifier in reversed(modifiers):
                user32.keybd_event(modifier, 0, KEYEVENTF_KEYUP, 0)
                events_sent += 1
                time.sleep(0.01)
            continue

        key_down = INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(0, ord(char), KEYEVENTF_UNICODE, 0, 0)))
        key_up = INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)))
        array_type = INPUT * 2
        sent = user32.SendInput(2, array_type(key_down, key_up), ctypes.sizeof(INPUT))
        if sent == 0:
            raise HTTPException(status_code=500, detail=f"Failed to send keyboard input to the desktop host for character: {char!r}")
        events_sent += int(sent)
        time.sleep(0.01)
    return events_sent


def _vk_code_for_key(key: str) -> int:
    lowered = key.strip().lower()
    if lowered in VK_CODES:
        return VK_CODES[lowered]
    if len(lowered) == 1:
        return ord(lowered.upper())
    raise HTTPException(status_code=400, detail=f"Unsupported hotkey segment: {key}")


def _parse_hotkey(keys: Any) -> list[str]:
    if isinstance(keys, list):
        return [str(item).strip() for item in keys if str(item).strip()]
    if isinstance(keys, str):
        return [segment.strip() for segment in keys.replace("+", " ").split() if segment.strip()]
    raise HTTPException(status_code=400, detail="press_hotkey requires a string like 'ctrl+l' or a keys array.")


def _press_hotkey(keys: Any) -> dict[str, Any]:
    if not _is_windows_host():
        raise HTTPException(status_code=400, detail="Hotkeys are only available on a native Windows desktop host.")
    parsed = _parse_hotkey(keys)
    if not parsed:
        raise HTTPException(status_code=400, detail="press_hotkey requires at least one key.")
    user32 = ctypes.windll.user32
    virtual_keys = [_vk_code_for_key(item) for item in parsed]
    for vk in virtual_keys:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)
    for vk in reversed(virtual_keys):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)
    return {"keys": parsed}


def _read_system_info() -> dict[str, Any]:
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def _capture_screen() -> tuple[dict[str, Any], str, str | None]:
    if not _is_windows_host():
        return (
            _diagnostic_artifact(
                "desktop-screen-unavailable",
                "Screen capture requires a native Windows desktop host and is not available inside the current runtime.",
                {"platform": platform.system()},
            ),
            "",
            "Screen capture requires a native Windows desktop host and is unavailable in the current runtime.",
        )

    try:
        image = ImageGrab.grab(all_screens=True)
    except Exception as exc:
        return (
            _diagnostic_artifact(
                "desktop-screen-error",
                f"Screen capture failed: {exc}",
                {"platform": platform.system(), "error": str(exc)},
            ),
            "",
            f"Screen capture failed in the current desktop runtime: {exc}",
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    text = ""
    if pytesseract and shutil.which("tesseract"):
        try:
            text = (pytesseract.image_to_string(image) or "").strip()
        except Exception:
            text = ""
    artifact = {
        "kind": "screenshot",
        "name": "desktop-screen",
        "mime_type": "image/png",
        "data_url": data_url,
        "metadata": {"ocr_available": bool(text)},
    }
    return artifact, text, None


def execute_actions(session_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    session = get_session(session_id)
    session.status = "busy"
    started = time.perf_counter()
    artifacts: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    processes: list[dict[str, Any]] = []
    system_info: dict[str, Any] | None = None
    extracted_text = ""
    warnings: list[str] = []
    action_results: list[dict[str, Any]] = []

    try:
        for action in actions:
            name = str(action.get("action") or "").strip()
            arguments = action.get("arguments") if isinstance(action.get("arguments"), dict) else {}
            if name == "list_windows":
                windows, warning = _enum_windows()
                _append_warning(warnings, warning)
                artifacts.append({"kind": "window_list", "metadata": {"count": len(windows)}, "windows": windows[:20]})
            elif name == "inspect_focused_window":
                active, warning = _foreground_window()
                _append_warning(warnings, warning)
                artifacts.append({"kind": "focused_window", "metadata": active or {}})
            elif name == "list_processes":
                processes, warning = _list_processes(limit=int(action.get("limit", 50)))
                _append_warning(warnings, warning)
                artifacts.append({"kind": "process_list", "metadata": {"count": len(processes)}, "processes": processes[:20]})
            elif name == "read_system_info":
                system_info = _read_system_info()
                artifacts.append({"kind": "system_info", "metadata": system_info})
            elif name == "capture_screen":
                artifact, ocr_text, warning = _capture_screen()
                _append_warning(warnings, warning)
                artifacts.append(artifact)
                if ocr_text:
                    extracted_text = ocr_text[:8000]
            elif name == "extract_text":
                artifact, ocr_text, warning = _capture_screen()
                _append_warning(warnings, warning)
                artifacts.append(artifact)
                extracted_text = (ocr_text or "")[:8000]
                if extracted_text:
                    artifacts.append({"kind": "ocr_text", "text": extracted_text})
            elif name == "get_accessibility_tree":
                active, warning = _foreground_window()
                _append_warning(warnings, warning)
                artifacts.append({
                    "kind": "accessibility_summary",
                    "text": f"Accessibility tree is not yet implemented. Active window: {(active or {}).get('title', 'unknown')}",
                    "metadata": active or {},
                })
            elif name == "focus_window":
                target = str(arguments.get("target") or action.get("target_window") or action.get("target_label") or "").strip() or None
                handle = arguments.get("handle")
                focus_result = _focus_window(target=target, handle=int(handle) if handle is not None else None)
                if not focus_result.get("focused"):
                    active_window = focus_result.get("active_window") or {}
                    requested_label = target or str(handle) or "requested window"
                    _append_warning(
                        warnings,
                        f"Requested focus target `{requested_label}` but the foreground window remained `{active_window.get('title', 'unknown')}`.",
                    )
                action_results.append({"action": name, **focus_result})
                artifacts.append({"kind": "desktop_action_result", "name": "focus_window", "metadata": focus_result})
            elif name == "launch_app":
                target_app = str(action.get("target_app") or arguments.get("target_app") or arguments.get("target") or "").strip() or None
                launch_result = _launch_app(target_app, arguments=arguments)
                action_results.append({"action": name, **launch_result})
                artifacts.append({"kind": "desktop_action_result", "name": "launch_app", "metadata": launch_result})
            elif name == "click":
                x = arguments.get("x")
                y = arguments.get("y")
                if x is None or y is None:
                    raise HTTPException(status_code=400, detail="click requires arguments.x and arguments.y")
                click_result = _click_at(int(x), int(y), button=str(arguments.get("button") or "left"), clicks=int(arguments.get("clicks") or 1))
                active_after_click, click_warning = _foreground_window()
                _append_warning(warnings, click_warning)
                expected_target = str(
                    action.get("target_window") or action.get("target_label") or arguments.get("target") or ""
                ).strip() or None
                click_result["active_window"] = active_after_click
                click_result["expected_target"] = expected_target
                if expected_target:
                    target_match = _window_matches_target(active_after_click, expected_target)
                    click_result["target_match"] = target_match
                    if not target_match and active_after_click:
                        _append_warning(
                            warnings,
                            f"Click focus drifted away from expected target `{expected_target}` and landed on `{active_after_click.get('title', 'unknown')}`.",
                        )
                action_results.append({"action": name, **click_result})
                artifacts.append({"kind": "desktop_action_result", "name": "click", "metadata": click_result})
            elif name == "type_text":
                text = str(arguments.get("text") or "").strip()
                if not text:
                    raise HTTPException(status_code=400, detail="type_text requires arguments.text")
                sent = _send_unicode_text(text)
                type_result = {"text": text, "characters": len(text), "send_input_events": sent}
                action_results.append({"action": name, **type_result})
                artifacts.append({"kind": "desktop_action_result", "name": "type_text", "metadata": type_result})
            elif name == "press_hotkey":
                hotkey_result = _press_hotkey(arguments.get("keys") or arguments.get("hotkey") or action.get("target_label"))
                action_results.append({"action": name, **hotkey_result})
                artifacts.append({"kind": "desktop_action_result", "name": "press_hotkey", "metadata": hotkey_result})
            else:
                raise HTTPException(status_code=400, detail=f"Desktop worker action not implemented: {name}")
    finally:
        session.status = "idle"

    duration_ms = int((time.perf_counter() - started) * 1000)
    active_window, active_warning = _foreground_window()
    _append_warning(warnings, active_warning)
    session.context_json = {
        **(session.context_json or {}),
        "focused_window": active_window,
        "last_action_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if warnings:
        artifacts.append(
            _diagnostic_artifact(
                "desktop-runtime-warning",
                " ".join(warnings[:3]),
                {"warning_count": len(warnings), "platform": platform.system()},
            )
        )
    return {
        "session_id": session.session_id,
        "actions": actions,
        "active_window": active_window,
        "focused_window": active_window,
        "windows": windows[:20],
        "processes": processes[:20],
        "system_info": system_info,
        "extracted_text": extracted_text,
        "action_results": action_results,
        "duration_ms": duration_ms,
        "status": "degraded" if warnings else "succeeded",
        "warnings": warnings,
        "environment": {
            "platform": platform.system(),
            "native_windows_host": _is_windows_host(),
        },
        "artifacts_json": artifacts,
    }
