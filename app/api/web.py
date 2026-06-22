"""Server-rendered dashboard routes."""

from app.api.web_actions import router as actions_router
from app.api.web_pages import router as pages_router

router = pages_router
router.include_router(actions_router)
