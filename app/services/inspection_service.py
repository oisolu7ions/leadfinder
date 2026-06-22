"""Website inspection orchestration — cheap checks, optional browser, persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.business_lead import BusinessLead
from app.models.website_inspection import WebsiteInspection
from app.services.audit import log_action
from app.services.browser_inspector import run_browser_inspection
from app.services.inspection_heuristics import (
    HtmlAnalysis,
    HttpFetcher,
    analyze_html,
    extract_internal_links,
    merge_html_analysis,
    run_prechecks,
)
from app.services.inspection_http import HttpxFetcher, social_precheck_result
from app.services.inspection_storage import artifact_paths, ensure_inspection_dirs
from app.services.scoring_service import score_lead

logger = get_logger(__name__)


def _effective_website_url(lead: BusinessLead) -> str | None:
    """Website or primary social/directory URL for inspection prechecks."""
    if lead.website_url:
        return lead.website_url
    if lead.social_links:
        for url in lead.social_links.values():
            if url:
                return url
    return None


def should_run_browser(
    *,
    settings: Settings,
    blank_website: bool,
    social_only: bool,
    reachable: bool | None,
    run_browser: bool | None,
) -> bool:
    """Decide whether Playwright inspection should run."""
    if run_browser is False:
        return False
    if run_browser is True:
        return settings.inspection_browser_enabled
    if not settings.inspection_browser_enabled:
        return False
    if blank_website or social_only:
        return False
    return reachable is True


def inspect_lead(
    db: Session,
    lead_id: int,
    *,
    run_browser: bool | None = None,
    auto_score: bool = True,
    http_fetcher: HttpFetcher | None = None,
    settings: Settings | None = None,
) -> WebsiteInspection:
    """Run the full inspection pipeline for a business lead."""
    settings = settings or get_settings()
    ensure_inspection_dirs(settings)

    lead = db.get(BusinessLead, lead_id)
    if lead is None:
        raise ValueError(f"Lead {lead_id} not found")

    fetcher = http_fetcher or HttpxFetcher()
    precheck = run_prechecks(_effective_website_url(lead))
    findings: dict = {
        "checks": list(precheck.checks),
        "browser_used": False,
        "http_used": False,
    }

    inspection = WebsiteInspection(business_lead_id=lead.id)
    inspection.blank_website = precheck.blank_website
    inspection.social_only = precheck.social_only
    inspection.branded_domain = precheck.branded_domain

    html_analysis = HtmlAnalysis()
    http_result = None

    if precheck.blank_website:
        inspection.reachable = False
        inspection.ssl_present = False
    elif precheck.social_only:
        http_result = social_precheck_result(precheck.website_url or "")
        inspection.final_url = http_result.final_url
        inspection.reachable = http_result.reachable
        inspection.ssl_present = http_result.ssl_present
        findings["checks"].append("social_host_skipped_fetch")
    else:
        http_result = fetcher.fetch(
            precheck.website_url or "",
            settings.inspection_timeout_seconds,
        )
        findings["http_used"] = True
        inspection.final_url = http_result.final_url
        inspection.http_status = http_result.http_status
        inspection.reachable = http_result.reachable
        inspection.ssl_present = http_result.ssl_present

        if http_result.error_message:
            inspection.error_message = http_result.error_message
            findings["checks"].append("http_fetch_failed")
        elif http_result.html:
            html_analysis = analyze_html(http_result.html, http_result.final_url)
            findings["checks"].append("http_fetch_ok")

            for link in extract_internal_links(http_result.html, http_result.final_url or ""):
                sub = fetcher.fetch(link, settings.inspection_timeout_seconds)
                if sub.html and sub.reachable:
                    html_analysis = merge_html_analysis(
                        html_analysis,
                        analyze_html(sub.html, sub.final_url),
                    )
                    findings["checks"].append(f"checked_link:{link}")

    inspection.page_title = html_analysis.page_title
    inspection.meta_description = html_analysis.meta_description
    inspection.has_contact_page = html_analysis.has_contact_page
    inspection.has_booking_flow = html_analysis.has_booking_flow
    inspection.mobile_friendly_basic = html_analysis.mobile_friendly_basic

    db.add(inspection)
    db.flush()

    if should_run_browser(
        settings=settings,
        blank_website=bool(inspection.blank_website),
        social_only=bool(inspection.social_only),
        reachable=inspection.reachable,
        run_browser=run_browser,
    ):
        screenshot_path = html_snapshot_path = None
        if settings.inspection_save_artifacts:
            screenshot_path, html_snapshot_path = artifact_paths(
                settings, lead.id, inspection.id
            )
            screenshot_path = str(screenshot_path)
            html_snapshot_path = str(html_snapshot_path)

        browser = run_browser_inspection(
            precheck.website_url or inspection.final_url or "",
            settings,
            screenshot_path=screenshot_path,
            html_snapshot_path=html_snapshot_path,
        )
        findings["browser_used"] = True
        findings["checks"].extend(browser.checks)

        if browser.error_message and not inspection.error_message:
            inspection.error_message = browser.error_message

        if browser.final_url:
            inspection.final_url = browser.final_url
        if browser.page_title:
            inspection.page_title = browser.page_title
        if browser.meta_description:
            inspection.meta_description = browser.meta_description
        if browser.mobile_friendly_basic is not False:
            inspection.mobile_friendly_basic = browser.mobile_friendly_basic
        inspection.has_contact_page = (
            inspection.has_contact_page or browser.has_contact_page
        )
        inspection.has_booking_flow = inspection.has_booking_flow or browser.has_booking_flow
        inspection.screenshot_path = browser.screenshot_path
        inspection.html_snapshot_path = browser.html_snapshot_path

        if browser.html:
            browser_html = analyze_html(browser.html, browser.final_url)
            inspection.has_contact_page = (
                inspection.has_contact_page or browser_html.has_contact_page
            )
            inspection.has_booking_flow = (
                inspection.has_booking_flow or browser_html.has_booking_flow
            )

    inspection.findings = findings
    inspection.inspected_at = datetime.now(UTC)
    db.flush()

    if auto_score:
        score_lead(db, lead.id, inspection=inspection)

    log_action(
        db,
        "inspection_completed",
        "business_lead",
        lead.id,
        details={"inspection_id": inspection.id, "findings": findings},
    )
    db.commit()
    db.refresh(inspection)

    logger.info(
        "inspection_completed",
        lead_id=lead_id,
        inspection_id=inspection.id,
        reachable=inspection.reachable,
        social_only=inspection.social_only,
        browser=findings.get("browser_used"),
    )
    return inspection


def get_inspection(db: Session, inspection_id: int) -> WebsiteInspection | None:
    return db.scalar(
        select(WebsiteInspection)
        .where(WebsiteInspection.id == inspection_id)
        .options(selectinload(WebsiteInspection.business_lead))
    )


def list_inspections(
    db: Session,
    *,
    lead_id: int | None = None,
    reachable: str | None = None,
    social_only: str | None = None,
    branded_domain: str | None = None,
    has_contact_page: str | None = None,
    has_booking_flow: str | None = None,
    ssl_present: str | None = None,
    has_error: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[WebsiteInspection]:
    stmt = select(WebsiteInspection).order_by(WebsiteInspection.inspected_at.desc())
    if lead_id is not None:
        stmt = stmt.where(WebsiteInspection.business_lead_id == lead_id)
    if reachable == "yes":
        stmt = stmt.where(WebsiteInspection.reachable.is_(True))
    elif reachable == "no":
        stmt = stmt.where(WebsiteInspection.reachable.is_(False))
    if social_only == "yes":
        stmt = stmt.where(WebsiteInspection.social_only.is_(True))
    elif social_only == "no":
        stmt = stmt.where(WebsiteInspection.social_only.is_(False))
    if branded_domain == "yes":
        stmt = stmt.where(WebsiteInspection.branded_domain.is_(True))
    elif branded_domain == "no":
        stmt = stmt.where(WebsiteInspection.branded_domain.is_(False))
    if has_contact_page == "yes":
        stmt = stmt.where(WebsiteInspection.has_contact_page.is_(True))
    elif has_contact_page == "no":
        stmt = stmt.where(WebsiteInspection.has_contact_page.is_(False))
    if has_booking_flow == "yes":
        stmt = stmt.where(WebsiteInspection.has_booking_flow.is_(True))
    elif has_booking_flow == "no":
        stmt = stmt.where(WebsiteInspection.has_booking_flow.is_(False))
    if ssl_present == "yes":
        stmt = stmt.where(WebsiteInspection.ssl_present.is_(True))
    elif ssl_present == "no":
        stmt = stmt.where(WebsiteInspection.ssl_present.is_(False))
    if has_error == "yes":
        stmt = stmt.where(WebsiteInspection.error_message.isnot(None))
    elif has_error == "no":
        stmt = stmt.where(WebsiteInspection.error_message.is_(None))
    stmt = stmt.offset(offset).limit(limit).options(selectinload(WebsiteInspection.business_lead))
    return list(db.scalars(stmt).unique().all())


def count_inspections(db: Session, lead_id: int | None = None) -> int:
    from sqlalchemy import func

    stmt = select(func.count()).select_from(WebsiteInspection)
    if lead_id is not None:
        stmt = stmt.where(WebsiteInspection.business_lead_id == lead_id)
    return db.scalar(stmt) or 0
