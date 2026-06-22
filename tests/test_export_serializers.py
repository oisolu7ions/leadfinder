"""Tests for export serializers."""

from datetime import UTC, datetime

from app.models.business_lead import BusinessLead
from app.models.lead_score import LeadScore
from app.models.outreach_draft import OutreachDraft
from app.models.website_inspection import WebsiteInspection
from app.services.export_serializers import EXPORT_CSV_COLUMNS, lead_to_export_row, row_to_csv_values


def test_export_columns_present() -> None:
    assert "lead_id" in EXPORT_CSV_COLUMNS
    assert "total_score" in EXPORT_CSV_COLUMNS
    assert "outreach_status" in EXPORT_CSV_COLUMNS
    assert "inspection_status" in EXPORT_CSV_COLUMNS


def test_lead_to_export_row_no_website() -> None:
    lead = BusinessLead(
        id=1,
        business_name="No Site Cafe",
        category="cafe",
        city="Austin",
        source_name="mock",
        status="new",
    )
    row = lead_to_export_row(lead)
    assert row["business_name"] == "No Site Cafe"
    assert row["inspection_status"] == "uninspected"
    assert row["total_score"] == ""
    values = row_to_csv_values(row)
    assert len(values) == len(EXPORT_CSV_COLUMNS)


def test_lead_to_export_row_with_related_data() -> None:
    lead = BusinessLead(
        id=2,
        business_name="Full Data Co",
        category="salon",
        city="Denver",
        website_url="https://example.com",
        source_name="mock",
        status="new",
    )
    lead.inspections = [
        WebsiteInspection(
            business_lead_id=2,
            reachable=True,
            social_only=False,
            branded_domain=True,
            has_contact_page=True,
            ssl_present=True,
            inspected_at=datetime.now(UTC),
        )
    ]
    lead.scores = [
        LeadScore(
            business_lead_id=2,
            total_score=55,
            no_website_score=0,
            social_only_score=0,
            branding_score=0,
            contact_flow_score=12,
            mobile_score=0,
            outdated_website_score=0,
            breakdown={"priority_tier": "high"},
        )
    ]
    lead.outreach_drafts = [
        OutreachDraft(
            business_lead_id=2,
            subject_line="Test subject",
            status="draft_ready",
        )
    ]
    row = lead_to_export_row(lead)
    assert row["inspection_status"] == "inspected"
    assert row["total_score"] == 55
    assert row["priority_tier"] == "high"
    assert row["outreach_status"] == "draft_ready"
    assert row["latest_draft_subject_line"] == "Test subject"
