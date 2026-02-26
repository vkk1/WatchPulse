from typing import Any

from app.core.config import settings
from app.db.client import get_supabase_client


def _latest_stats_by_model(model_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not model_ids:
        return {}

    client = get_supabase_client()
    stats_response = (
        client.table("model_daily_stats")
        .select("model_id,captured_date,median_price,wait_band,wait_time_index")
        .in_("model_id", model_ids)
        .order("captured_date", desc=True)
        .execute()
    )
    latest: dict[int, dict[str, Any]] = {}
    for row in stats_response.data or []:
        model_id = row["model_id"]
        if model_id not in latest:
            latest[model_id] = row
    return latest


def list_models(*, page: int, page_size: int, q: str | None = None, collection: str | None = None) -> dict[str, Any]:
    client = get_supabase_client()
    start = (page - 1) * page_size
    end = start + page_size - 1

    query = (
        client.table("brand_models")
        .select(
            "id,brand,collection,model_name,ref_code,msrp,case_material,bracelet,dial,size_mm,image_url",
            count="exact",
        )
        .eq("brand", settings.rolex_brand)
    )
    if collection:
        query = query.ilike("collection", f"%{collection}%")
    if q:
        safe_q = q.replace(",", " ").strip()
        query = query.or_(f"model_name.ilike.%{safe_q}%,ref_code.ilike.%{safe_q}%")

    response = query.order("collection").order("model_name").range(start, end).execute()
    models = response.data or []
    model_ids = [row["id"] for row in models]
    latest_map = _latest_stats_by_model(model_ids)

    items: list[dict[str, Any]] = []
    for row in models:
        latest = latest_map.get(row["id"], {})
        items.append(
            {
                "id": row["id"],
                "brand": row["brand"],
                "collection": row["collection"],
                "model_name": row["model_name"],
                "ref_code": row["ref_code"],
                "msrp": row["msrp"],
                "image_url": row["image_url"],
                "current_median_price": latest.get("median_price"),
                "wait_band": latest.get("wait_band"),
                "wait_time_index": latest.get("wait_time_index"),
            }
        )

    total = response.count or 0
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "items": items,
    }


def get_model_detail(model_id: int) -> dict[str, Any] | None:
    client = get_supabase_client()
    model_response = (
        client.table("brand_models")
        .select("*")
        .eq("id", model_id)
        .eq("brand", settings.rolex_brand)
        .limit(1)
        .execute()
    )
    models = model_response.data or []
    if not models:
        return None

    stats_response = (
        client.table("model_daily_stats")
        .select(
            "captured_date,median_price,listings_count,new_listings_count,sold_rate_proxy,premium_over_msrp,wait_time_index,wait_band"
        )
        .eq("model_id", model_id)
        .order("captured_date", desc=False)
        .execute()
    )

    return {
        "model": models[0],
        "daily_stats": stats_response.data or [],
    }
