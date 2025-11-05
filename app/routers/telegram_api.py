from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.telegram.registry import (
    create_link_code, create_subscription, toggle_subscription
)

router = APIRouter(prefix="/telegram", tags=["Telegram API"])

class LinkReq(BaseModel):
    external_user_id: str
    ttl_minutes: int = Field(default=15, ge=1, le=120)

@router.post("/link-code")
def api_link_code(payload: LinkReq):
    return create_link_code(payload.external_user_id, payload.ttl_minutes)

class SubReq(BaseModel):
    external_user_id: str
    symbol: str
    interval: str = "1m"
    window: int = 20
    multiplier: float = 2.0

@router.post("/subscriptions/create")
def api_create_sub(payload: SubReq):
    try:
        sub_id = create_subscription(
            payload.external_user_id, payload.symbol,
            payload.interval, payload.window, payload.multiplier
        )
        return {"subscription_id": sub_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class ToggleReq(BaseModel):
    subscription_id: int
    is_active: bool

@router.post("/subscriptions/toggle")
def api_toggle(payload: ToggleReq):
    ok = toggle_subscription(payload.subscription_id, payload.is_active)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"subscription_id": payload.subscription_id, "is_active": payload.is_active}
