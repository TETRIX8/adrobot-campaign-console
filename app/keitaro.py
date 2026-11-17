from __future__ import annotations

from typing import Any

import httpx

from .config import settings


class KeitaroError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class KeitaroClient:
    def __init__(self) -> None:
        self.base_url = settings.keitaro_api_url
        self.timeout = settings.keitaro_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Api-Key": settings.keitaro_api_key, "Accept": "application/json", "Content-Type": "application/json"}

    async def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> Any:
        if not settings.configured:
            raise KeitaroError("Keitaro API не настроен: добавьте KEITARO_API_KEY в .env")
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=self._headers(), params=params, json=json)
        except httpx.HTTPError as exc:
            raise KeitaroError(f"Не удалось подключиться к Keitaro: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        if response.is_error:
            detail = payload.get("message") if isinstance(payload, dict) else str(payload)
            raise KeitaroError(f"Keitaro вернул HTTP {response.status_code}: {detail}", response.status_code, payload)
        return payload

    async def catalog(self) -> dict[str, Any]:
        campaigns, offers, domains, groups, sources = await self._parallel_catalog()
        return {"campaigns": campaigns, "offers": offers, "domains": domains, "groups": groups, "traffic_sources": sources}

    async def _parallel_catalog(self) -> tuple[list[Any], list[Any], list[Any], list[Any], list[Any]]:
        import asyncio
        return await asyncio.gather(
            self.list("campaigns", params={"limit": 100, "offset": 0}),
            self.list("offers"),
            self.list("domains"),
            self.list("groups", params={"type": "campaigns"}),
            self.list("traffic_sources"),
        )

    async def list(self, resource: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        result = await self.request("GET", resource, params=params)
        return result if isinstance(result, list) else result.get("data", []) if isinstance(result, dict) else []

    async def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        return await self.request("GET", f"campaigns/{campaign_id}")

    async def get_streams(self, campaign_id: int) -> list[Any]:
        result = await self.request("GET", f"campaigns/{campaign_id}/streams")
        return result if isinstance(result, list) else []

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "campaigns", json=payload)

    async def create_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "streams", json=payload)

    async def update_stream(self, stream_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", f"streams/{stream_id}", json=payload)


def item_id(item: dict[str, Any]) -> int | None:
    value = item.get("id")
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def item_name(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("title") or f"#{item.get('id', '—')}")
