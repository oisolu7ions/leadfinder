"""Initial schema — core entities for OIS Lead Discovery Platform.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sources_name"), "sources", ["name"], unique=True)

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_export_jobs_status"), "export_jobs", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)

    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("query_text", sa.String(length=500), nullable=True),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_found", sa.Integer(), nullable=False),
        sa.Column("total_inserted", sa.Integer(), nullable=False),
        sa.Column("total_updated", sa.Integer(), nullable=False),
        sa.Column("total_flagged", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("logs_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_jobs_category"), "scan_jobs", ["category"], unique=False)
    op.create_index(op.f("ix_scan_jobs_city"), "scan_jobs", ["city"], unique=False)
    op.create_index(op.f("ix_scan_jobs_source_name"), "scan_jobs", ["source_name"], unique=False)
    op.create_index(op.f("ix_scan_jobs_state"), "scan_jobs", ["state"], unique=False)
    op.create_index(op.f("ix_scan_jobs_status"), "scan_jobs", ["status"], unique=False)

    op.create_table(
        "business_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("scan_job_id", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("business_name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address_line1", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("website_url", sa.String(length=2000), nullable=True),
        sa.Column("normalized_domain", sa.String(length=500), nullable=True),
        sa.Column("social_links", sa.JSON(), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", "external_id", name="uq_lead_source_external_id"),
    )
    op.create_index("ix_leads_dedup_domain", "business_leads", ["normalized_domain"], unique=False)
    op.create_index("ix_leads_dedup_name_city", "business_leads", ["normalized_name", "city"], unique=False)
    op.create_index("ix_leads_dedup_phone", "business_leads", ["phone"], unique=False)
    op.create_index(op.f("ix_business_leads_business_name"), "business_leads", ["business_name"], unique=False)
    op.create_index(op.f("ix_business_leads_category"), "business_leads", ["category"], unique=False)
    op.create_index(op.f("ix_business_leads_city"), "business_leads", ["city"], unique=False)
    op.create_index(op.f("ix_business_leads_external_id"), "business_leads", ["external_id"], unique=False)
    op.create_index(op.f("ix_business_leads_normalized_domain"), "business_leads", ["normalized_domain"], unique=False)
    op.create_index(op.f("ix_business_leads_normalized_name"), "business_leads", ["normalized_name"], unique=False)
    op.create_index(op.f("ix_business_leads_phone"), "business_leads", ["phone"], unique=False)
    op.create_index(op.f("ix_business_leads_scan_job_id"), "business_leads", ["scan_job_id"], unique=False)
    op.create_index(op.f("ix_business_leads_source_name"), "business_leads", ["source_name"], unique=False)
    op.create_index(op.f("ix_business_leads_state"), "business_leads", ["state"], unique=False)
    op.create_index(op.f("ix_business_leads_status"), "business_leads", ["status"], unique=False)

    op.create_table(
        "lead_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_lead_id", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("no_website_score", sa.Integer(), nullable=False),
        sa.Column("outdated_website_score", sa.Integer(), nullable=False),
        sa.Column("mobile_score", sa.Integer(), nullable=False),
        sa.Column("branding_score", sa.Integer(), nullable=False),
        sa.Column("contact_flow_score", sa.Integer(), nullable=False),
        sa.Column("social_only_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["business_lead_id"], ["business_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lead_scores_business_lead_id"), "lead_scores", ["business_lead_id"], unique=False)
    op.create_index(op.f("ix_lead_scores_total_score"), "lead_scores", ["total_score"], unique=False)

    op.create_table(
        "outreach_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_lead_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tone", sa.String(length=50), nullable=False),
        sa.Column("subject_line", sa.String(length=500), nullable=True),
        sa.Column("email_body", sa.Text(), nullable=True),
        sa.Column("short_dm", sa.Text(), nullable=True),
        sa.Column("call_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["business_lead_id"], ["business_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outreach_drafts_business_lead_id"), "outreach_drafts", ["business_lead_id"], unique=False)
    op.create_index(op.f("ix_outreach_drafts_status"), "outreach_drafts", ["status"], unique=False)

    op.create_table(
        "website_inspections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_lead_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_url", sa.String(length=2000), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("reachable", sa.Boolean(), nullable=True),
        sa.Column("blank_website", sa.Boolean(), nullable=True),
        sa.Column("social_only", sa.Boolean(), nullable=True),
        sa.Column("branded_domain", sa.Boolean(), nullable=True),
        sa.Column("mobile_friendly_basic", sa.Boolean(), nullable=True),
        sa.Column("has_contact_page", sa.Boolean(), nullable=True),
        sa.Column("has_booking_flow", sa.Boolean(), nullable=True),
        sa.Column("ssl_present", sa.Boolean(), nullable=True),
        sa.Column("page_title", sa.String(length=500), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("technologies", sa.JSON(), nullable=True),
        sa.Column("screenshot_path", sa.String(length=1000), nullable=True),
        sa.Column("html_snapshot_path", sa.String(length=1000), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["business_lead_id"], ["business_leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_website_inspections_business_lead_id"),
        "website_inspections",
        ["business_lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_website_inspections_business_lead_id"), table_name="website_inspections")
    op.drop_table("website_inspections")
    op.drop_index(op.f("ix_outreach_drafts_status"), table_name="outreach_drafts")
    op.drop_index(op.f("ix_outreach_drafts_business_lead_id"), table_name="outreach_drafts")
    op.drop_table("outreach_drafts")
    op.drop_index(op.f("ix_lead_scores_total_score"), table_name="lead_scores")
    op.drop_index(op.f("ix_lead_scores_business_lead_id"), table_name="lead_scores")
    op.drop_table("lead_scores")
    op.drop_index(op.f("ix_business_leads_status"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_state"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_source_name"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_scan_job_id"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_phone"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_normalized_name"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_normalized_domain"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_external_id"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_city"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_category"), table_name="business_leads")
    op.drop_index(op.f("ix_business_leads_business_name"), table_name="business_leads")
    op.drop_index("ix_leads_dedup_phone", table_name="business_leads")
    op.drop_index("ix_leads_dedup_name_city", table_name="business_leads")
    op.drop_index("ix_leads_dedup_domain", table_name="business_leads")
    op.drop_table("business_leads")
    op.drop_index(op.f("ix_scan_jobs_status"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_state"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_source_name"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_city"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_category"), table_name="scan_jobs")
    op.drop_table("scan_jobs")
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_export_jobs_status"), table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index(op.f("ix_sources_name"), table_name="sources")
    op.drop_table("sources")
