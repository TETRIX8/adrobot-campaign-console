from typing import Any

from pydantic import BaseModel, Field, field_validator


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    geo: list[str] = Field(min_length=1, max_length=30)
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)

    @field_validator("geo")
    @classmethod
    def normalize_geo(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().upper() for item in value if item.strip()]
        if not normalized:
            raise ValueError("Укажите хотя бы один ISO-код страны")
        if any(len(item) != 2 or not item.isalpha() for item in normalized):
            raise ValueError("Geo должен содержать ISO-коды из двух букв, например RU или DE")
        return list(dict.fromkeys(normalized))


class OfferMutationRequest(BaseModel):
    offer_id: int = Field(gt=0)
    share: int = Field(default=100, ge=1, le=100)


class ApiMessage(BaseModel):
    ok: bool
    message: str
    data: Any | None = None
