"""Backward-compatible re-exports — use inspection_service directly."""

from app.services.inspection_service import inspect_lead


def inspect_leads_batch(db, lead_ids: list[int]):
    """Inspect multiple leads sequentially (sync)."""
    from app.services.inspection_service import inspect_lead as _inspect

    results = []
    for lead_id in lead_ids:
        try:
            results.append(_inspect(db, lead_id))
        except Exception:
            db.rollback()
    return results
