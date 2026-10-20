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
    outfits,
    photos,
    places,
    plan,
    profile,
    reference,
    suggestions,
    trips,
    wear_logs,
)
from app.api.deps import require_requested_with

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_requested_with)])
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(reference.router)
api_router.include_router(profile.router)
api_router.include_router(places.router)
api_router.include_router(brand_notes.router)
api_router.include_router(categories.router)
api_router.include_router(photos.router)
api_router.include_router(items.router)
api_router.include_router(suggestions.suggest_router)
api_router.include_router(outfits.router)
api_router.include_router(suggestions.router)
api_router.include_router(wear_logs.router)
api_router.include_router(plan.router)
api_router.include_router(trips.router)
api_router.include_router(insights.router)
