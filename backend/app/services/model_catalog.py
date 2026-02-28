from typing import Any

from app.core.config import settings
from app.db.client import get_supabase_client

ALLOWED_SORTS = {
    "wait_time_index_desc",
    "premium_desc",
    "price_asc",
    "price_desc",
}


def _latest_stats_by_model(model_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not model_ids:
        return {}

    client = get_supabase_client()
    # Preferred query shape: one row per model from a DISTINCT ON view.
    try:
        view_response = (
            client.table("model_latest_stats")
            .select("model_id,median_price,wait_band,wait_time_index,premium_over_msrp")
            .in_("model_id", model_ids)
            .execute()
        )
        return {int(row["model_id"]): row for row in (view_response.data or [])}
    except Exception:
        # Backward-compatible fallback if the view has not been created yet.
        stats_response = (
            client.table("model_daily_stats")
            .select("model_id,captured_date,median_price,wait_band,wait_time_index,premium_over_msrp")
            .in_("model_id", model_ids)
            .order("model_id")
            .order("captured_date", desc=True)
            .execute()
        )
        latest: dict[int, dict[str, Any]] = {}
        for row in stats_response.data or []:
            model_id = int(row["model_id"])
            if model_id not in latest:
                latest[model_id] = row
        return latest


def _sort_items(items: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    def null_last(value: Any, fallback: float) -> float:
        if value is None:
            return fallback
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    if sort == "premium_desc":
        return sorted(items, key=lambda x: null_last(x.get("premium_over_msrp"), -10_000.0), reverse=True)
    if sort == "price_asc":
        return sorted(items, key=lambda x: null_last(x.get("current_median_price"), 10_000_000_000.0))
    if sort == "price_desc":
        return sorted(items, key=lambda x: null_last(x.get("current_median_price"), -1.0), reverse=True)
    # default and explicit wait_time_index_desc
    return sorted(items, key=lambda x: null_last(x.get("wait_time_index"), -10_000.0), reverse=True)


def list_models(
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    collection: str | None = None,
    sort: str = "wait_time_index_desc",
) -> dict[str, Any]:
    client = get_supabase_client()
    safe_sort = sort if sort in ALLOWED_SORTS else "wait_time_index_desc"

    query = (
        client.table("brand_models")
        .select(
            "id,brand,collection,model_name,ref_code,msrp,image_url",
        )
        .eq("brand", settings.rolex_brand)
    )
    if collection:
        query = query.ilike("collection", f"%{collection}%")
    if q:
        safe_q = q.replace(",", " ").strip()
        query = query.or_(f"model_name.ilike.%{safe_q}%,ref_code.ilike.%{safe_q}%")

    # Fetch filtered models first, then sort by latest derived metrics in memory.
    response = query.order("collection").order("model_name").execute()
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
                "premium_over_msrp": latest.get("premium_over_msrp"),
                "wait_band": latest.get("wait_band"),
                "wait_time_index": latest.get("wait_time_index"),
            }
        )

    sorted_items = _sort_items(items, safe_sort)
    total = len(sorted_items)
    total_pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = sorted_items[start:end]
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "sort": safe_sort,
        "items": paged_items,
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
