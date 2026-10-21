"""Every route lives under /api/v1, and every state-changing request needs a custom header."""

from fastapi import APIRouter, Depends

from app.api import (
    account,
    auth,
    brand_notes,
    categories,
    health,
    insights,
    items,
    ops,
    outfits,
    photos,
    places,
    plan,
    profile,
    reference,
    shopping,
    stylist,
    suggestions,
    trips,
    wear_logs,
)
from app.api.deps import require_requested_with, write_budget

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_requested_with)])
# Open to anyone: the health check, logging in and out, and the browser's error reports (each
# with its own limits).
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(ops.reports)
# Everything else is a person's own data, and every change counts against their budget. The
# order matters: /outfits/suggest must come before /outfits/{outfit_id}.
for router in (
    account.router,
    reference.router,
    profile.router,
    places.router,
    brand_notes.router,
    categories.router,
    photos.router,
    items.router,
    suggestions.suggest_router,
    outfits.router,
    suggestions.router,
    wear_logs.router,
    plan.router,
    trips.router,
    insights.router,
    shopping.router,
    stylist.router,
    ops.admin,
):
    api_router.include_router(router, dependencies=[Depends(write_budget)])
