from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .keitaro import KeitaroClient, KeitaroError, item_id, item_name
from .models import OperationLog
from .schemas import CreateCampaignRequest, OfferMutationRequest

router = APIRouter(prefix="/api")
client = KeitaroClient()


def record(db: Session, operation: str, status: str, message: str, resource_id: int | str | None = None) -> None:
    db.add(OperationLog(operation=operation, status=status, message=message, resource_id=str(resource_id) if resource_id else None))
    db.commit()


def api_error(exc: KeitaroError) -> HTTPException:
    return HTTPException(status_code=502 if not exc.status_code or exc.status_code >= 500 else exc.status_code, detail=str(exc))


@router.get("/config")
async def config_status() -> dict:
    return {"configured": settings.configured, "base_url": settings.keitaro_base_url, "demo_mode": settings.demo_mode and not settings.configured}


@router.get("/catalog")
async def catalog() -> dict:
    if not settings.configured:
        return {"campaigns": [], "offers": [], "domains": [], "groups": [], "traffic_sources": [], "demo": True}
    try:
        return {**await client.catalog(), "demo": False}
    except KeitaroError as exc:
        raise api_error(exc)


@router.get("/campaigns/{campaign_id}")
async def campaign(campaign_id: int) -> dict:
    if not settings.configured:
        raise HTTPException(status_code=503, detail="Keitaro API не настроен")
    try:
        campaign_data, streams = await __import__("asyncio").gather(client.get_campaign(campaign_id), client.get_streams(campaign_id))
        offers = []
        for stream in streams:
            for offer in stream.get("offers", []) if isinstance(stream, dict) else []:
                offers.append({**offer, "stream_id": stream.get("id"), "stream_name": stream.get("name")})
        return {"campaign": campaign_data, "streams": streams, "offers": offers, "offer_count": len(offers), "stream_count": len(streams)}
    except KeitaroError as exc:
        raise api_error(exc)


@router.post("/campaigns/create")
async def create_campaign(payload: CreateCampaignRequest, db: Session = Depends(get_db)) -> dict:
    if not settings.configured:
        raise HTTPException(status_code=503, detail="Keitaro API не настроен. Укажите API-ключ в .env")
    campaign_payload = {
        "name": payload.name,
        "alias": "-".join(payload.name.lower().split()),
        "type": "position",
        "state": "active",
        "domain_id": payload.domain_id,
        "group_id": payload.group_id,
        "traffic_source_id": payload.traffic_source_id,
    }
    try:
        created = await client.create_campaign(campaign_payload)
        campaign_id = item_id(created) or int(created.get("id"))
        await client.create_stream({
            "campaign_id": campaign_id,
            "type": "regular",
            "name": "Geo gate → Google",
            "schema": "redirect",
            "action_type": "http",
            "action_options": {"url": "https://www.google.com"},
            "filters": [{"name": "country", "mode": "accept", "payload": payload.geo}],
            "state": "active",
            "position": 1,
        })
        offer_stream = await client.create_stream({
            "campaign_id": campaign_id,
            "type": "default",
            "name": "Selected offer",
            "schema": "redirect",
            "action_type": "offer",
            "offers": [{"offer_id": payload.offer_id, "share": 100, "state": "active"}],
            "state": "active",
            "position": 2,
        })
        message = f"Кампания создана: {campaign_id}. Созданы 2 потока."
        record(db, "campaign.create", "success", message, campaign_id)
        return {"ok": True, "message": message, "campaign": created, "offer_stream": offer_stream}
    except KeitaroError as exc:
        record(db, "campaign.create", "error", str(exc))
        raise api_error(exc)


@router.post("/campaigns/{campaign_id}/offers")
async def add_offer(campaign_id: int, payload: OfferMutationRequest, db: Session = Depends(get_db)) -> dict:
    if not settings.configured:
        raise HTTPException(status_code=503, detail="Keitaro API не настроен")
    try:
        streams = await client.get_streams(campaign_id)
        target = next((s for s in streams if s.get("type") in {"default", "regular"}), None)
        if not target:
            target = await client.create_stream({"campaign_id": campaign_id, "type": "default", "name": "Offer editor", "schema": "redirect", "action_type": "offer", "offers": []})
        current = target.get("offers", []) or []
        existing = {int(o.get("offer_id")) for o in current if o.get("offer_id") is not None}
        if payload.offer_id not in existing:
            current.append({"offer_id": payload.offer_id, "share": payload.share, "state": "active"})
        updated = await client.update_stream(int(target["id"]), {"offers": current})
        message = f"Оффер {payload.offer_id} добавлен в поток {target['id']}."
        record(db, "campaign.offer.add", "success", message, campaign_id)
        return {"ok": True, "message": message, "stream": updated}
    except KeitaroError as exc:
        record(db, "campaign.offer.add", "error", str(exc), campaign_id)
        raise api_error(exc)


@router.delete("/campaigns/{campaign_id}/offers/{offer_id}")
async def delete_offer(campaign_id: int, offer_id: int, db: Session = Depends(get_db)) -> dict:
    if not settings.configured:
        raise HTTPException(status_code=503, detail="Keitaro API не настроен")
    try:
        streams = await client.get_streams(campaign_id)
        changed = []
        for stream in streams:
            offers = stream.get("offers", []) or []
            filtered = [o for o in offers if int(o.get("offer_id", -1)) != offer_id]
            if len(filtered) != len(offers):
                changed.append(await client.update_stream(int(stream["id"]), {"offers": filtered}))
        message = f"Оффер {offer_id} удалён из {len(changed)} потоков."
        record(db, "campaign.offer.delete", "success", message, campaign_id)
        return {"ok": True, "message": message, "updated_streams": changed}
    except (KeitaroError, ValueError) as exc:
        if isinstance(exc, KeitaroError):
            record(db, "campaign.offer.delete", "error", str(exc), campaign_id)
            raise api_error(exc)
        raise HTTPException(status_code=400, detail="Некорректный offer_id")


@router.get("/operations")
def operations(limit: int = 20, db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "operation": row.operation, "status": row.status, "resource_id": row.resource_id, "message": row.message, "created_at": row.created_at.isoformat() if row.created_at else None} for row in db.query(OperationLog).order_by(OperationLog.id.desc()).limit(min(limit, 100)).all()]
