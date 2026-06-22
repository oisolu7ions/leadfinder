"""Audit trail logging."""

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    actor: str = "dashboard",
    details: dict | None = None,
) -> AuditLog:
    """Record an audit log entry."""
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    db.flush()
    return entry
