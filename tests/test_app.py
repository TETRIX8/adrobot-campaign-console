from app.keitaro import item_id, item_name
from app.schemas import CreateCampaignRequest


def test_item_helpers_normalize_keitaro_records():
    assert item_id({"id": "42"}) == 42
    assert item_name({"id": 42}) == "#42"


def test_campaign_request_normalizes_geo_codes():
    request = CreateCampaignRequest(name="Test", geo=["ru", " RU ", "de"], offer_id=1, domain_id=2, group_id=3, traffic_source_id=4)
    assert request.geo == ["RU", "DE"]
