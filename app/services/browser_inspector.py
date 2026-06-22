"""Optional Playwright-based website inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.inspection_heuristics import HtmlAnalysis, analyze_html

logger = get_logger(__name__)

MOBILE_VIEWPORT = {"width": 390, "height": 844}


@dataclass
class BrowserInspectionResult:
    final_url: str | None = None
    page_title: str | None = None
    meta_description: str | None = None
    mobile_friendly_basic: bool = False
    has_contact_page: bool = False
    has_booking_flow: bool = False
    screenshot_path: str | None = None
    html_snapshot_path: str | None = None
    html: str = ""
    checks: list[str] = field(default_factory=list)
    error_message: str | None = None


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def run_browser_inspection(
    url: str,
    settings: Settings,
    *,
    screenshot_path: str | None = None,
    html_snapshot_path: str | None = None,
    timeout_ms: int | None = None,
) -> BrowserInspectionResult:
    """Run a single-page Playwright inspection with mobile viewport."""
    if not settings.inspection_browser_enabled:
        return BrowserInspectionResult(error_message="Browser inspection disabled")

    if not playwright_available():
        return BrowserInspectionResult(error_message="Playwright not installed")

    timeout_ms = timeout_ms or settings.inspection_timeout_seconds * 1000
    result = BrowserInspectionResult()

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport=MOBILE_VIEWPORT,
                    user_agent=(
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                    ),
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                result.final_url = page.url
                html = page.content()
                result.html = html[:500_000]

                analysis = analyze_html(html, page.url)
                result.page_title = analysis.page_title
                result.meta_description = analysis.meta_description
                result.has_contact_page = analysis.has_contact_page
                result.has_booking_flow = analysis.has_booking_flow

                # Mobile heuristic: viewport meta + no horizontal overflow at mobile width
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth > window.innerWidth + 20"
                )
                result.mobile_friendly_basic = analysis.mobile_friendly_basic and not overflow
                result.checks.append("browser_mobile_viewport")

                visible_text = page.inner_text("body")[:50_000].lower()
                if any(k in visible_text for k in ("contact", "get in touch", "email us")):
                    result.has_contact_page = True
                if any(
                    k in visible_text
                    for k in ("book now", "schedule", "appointment", "reservation", "order online")
                ):
                    result.has_booking_flow = True
                    result.checks.append("browser_booking_cta")

                if settings.inspection_save_artifacts:
                    if screenshot_path:
                        page.screenshot(path=screenshot_path, full_page=False)
                        result.screenshot_path = screenshot_path
                        result.checks.append("screenshot_saved")
                    if html_snapshot_path:
                        Path(html_snapshot_path).write_text(html[:500_000], encoding="utf-8")
                        result.html_snapshot_path = html_snapshot_path
                        result.checks.append("html_snapshot_saved")

                result.checks.append("browser_inspection_ok")
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("browser_inspection_failed", url=url, error=str(exc))
        result.error_message = str(exc)
        result.checks.append("browser_inspection_failed")

    return result
