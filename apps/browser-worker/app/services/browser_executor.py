from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

from fastapi import HTTPException
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import get_settings

settings = get_settings()


@dataclass
class BrowserSession:
    session_id: str
    workspace_id: str
    session_type: str
    reusable: bool
    context_json: dict[str, Any]
    context: BrowserContext
    page: Page
    status: str = "idle"


PLAYWRIGHT = None
BROWSER: Browser | None = None
SESSIONS: dict[str, BrowserSession] = {}


def normalize_browser_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return raw_url

    host = "host.docker.internal"
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"
    else:
        netloc = host

    return urlunparse(parsed._replace(netloc=netloc))


async def startup_browser() -> None:
    global PLAYWRIGHT, BROWSER
    PLAYWRIGHT = await async_playwright().start()
    BROWSER = await PLAYWRIGHT.chromium.launch(headless=settings.BROWSER_WORKER_HEADLESS)


async def shutdown_browser() -> None:
    global PLAYWRIGHT, BROWSER
    for session_id in list(SESSIONS.keys()):
        await close_session(session_id)
    if BROWSER is not None:
        await BROWSER.close()
        BROWSER = None
    if PLAYWRIGHT is not None:
        await PLAYWRIGHT.stop()
        PLAYWRIGHT = None


async def create_session(*, session_id: str, workspace_id: str, session_type: str, reusable: bool, context_json: dict[str, Any]) -> BrowserSession:
    if BROWSER is None:
        raise HTTPException(status_code=503, detail="Browser runtime is not ready")
    context = await BROWSER.new_context(ignore_https_errors=True)
    page = await context.new_page()
    session = BrowserSession(
        session_id=session_id,
        workspace_id=workspace_id,
        session_type=session_type,
        reusable=reusable,
        context_json=context_json,
        context=context,
        page=page,
    )
    SESSIONS[session_id] = session
    return session


async def get_session(session_id: str) -> BrowserSession:
    session = SESSIONS.get(session_id)
    if not session or session.status == "closed":
        raise HTTPException(status_code=404, detail="Browser session not found")
    return session


async def close_session(session_id: str) -> None:
    session = await get_session(session_id)
    session.status = "closed"
    await session.context.close()
    SESSIONS.pop(session_id, None)


async def execute_actions(session_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    session = await get_session(session_id)
    session.status = "busy"
    page = session.page
    extracted_text = ""
    artifacts: list[dict[str, Any]] = []
    started = time.perf_counter()

    try:
        for action in actions:
            name = action.get("action")
            if name == "open_url":
                url = action.get("url")
                if not url:
                    raise HTTPException(status_code=400, detail="open_url requires a url")
                normalized_url = normalize_browser_url(str(url))
                await page.goto(normalized_url, wait_until="load")
            elif name == "click":
                selector = action.get("selector")
                if not selector:
                    raise HTTPException(status_code=400, detail="click requires a selector")
                await page.click(str(selector))
            elif name == "hover":
                selector = action.get("selector")
                if not selector:
                    raise HTTPException(status_code=400, detail="hover requires a selector")
                await page.hover(str(selector))
            elif name == "type":
                selector = action.get("selector")
                text = action.get("text", "")
                if not selector:
                    raise HTTPException(status_code=400, detail="type requires a selector")
                await page.locator(str(selector)).fill(str(text))
            elif name == "select_option":
                selector = action.get("selector")
                value = action.get("value")
                if not selector:
                    raise HTTPException(status_code=400, detail="select_option requires a selector")
                if value is None:
                    raise HTTPException(status_code=400, detail="select_option requires a value")
                await page.locator(str(selector)).select_option(str(value))
            elif name == "press":
                key = action.get("key") or "Enter"
                await page.keyboard.press(str(key))
            elif name == "wait_for":
                if action.get("selector"):
                    await page.wait_for_selector(str(action["selector"]))
                elif action.get("text"):
                    await page.wait_for_selector(f"text={action['text']}")
                else:
                    await page.wait_for_timeout(int(float(action.get("time", 1)) * 1000))
            elif name == "extract_text":
                selector = action.get("selector")
                if selector:
                    extracted_text = await page.locator(str(selector)).inner_text()
                else:
                    extracted_text = await page.locator("body").inner_text()
                    extracted_text = extracted_text[:12000]
            elif name == "extract_links":
                selector = str(action.get("selector") or "a")
                limit = max(1, min(int(action.get("limit", 20)), 100))
                links = await page.locator(selector).evaluate_all(
                    """(elements, limit) => elements.slice(0, limit).map((element) => ({
                        text: (element.textContent || '').trim(),
                        href: element.href || element.getAttribute('href') || ''
                    }))""",
                    limit,
                )
                artifacts.append({"kind": "links", "links": links})
            elif name == "take_screenshot":
                screenshot = await page.screenshot(type="png", full_page=bool(action.get("full_page", True)))
                name_value = str(action.get("name") or f"shot-{len(artifacts)+1}")
                artifacts.append({
                    "kind": "screenshot",
                    "name": name_value,
                    "mime_type": "image/png",
                    "data_url": "data:image/png;base64," + base64.b64encode(screenshot).decode("ascii"),
                })
            elif name == "list_tabs":
                tabs = []
                for index, p in enumerate(session.context.pages):
                    tabs.append({"index": index, "url": p.url, "title": await p.title()})
                artifacts.append({"kind": "tabs", "tabs": tabs})
            elif name == "close_tab":
                target_index = int(action.get("index", len(session.context.pages) - 1))
                pages = session.context.pages
                if target_index < 0 or target_index >= len(pages):
                    raise HTTPException(status_code=400, detail="close_tab index is out of range")
                await pages[target_index].close()
                if session.context.pages:
                    session.page = session.context.pages[0]
                    page = session.page
                else:
                    session.page = await session.context.new_page()
                    page = session.page
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported browser action: {name}")
    finally:
        session.status = "idle"

    session.context_json = {
        **(session.context_json or {}),
        "current_url": page.url,
        "title": await page.title(),
        "tabs": [p.url for p in session.context.pages],
    }
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "session_id": session.session_id,
        "actions": actions,
        "current_url": page.url,
        "title": await page.title(),
        "extracted_text": extracted_text,
        "duration_ms": duration_ms,
        "artifacts_json": artifacts,
    }
