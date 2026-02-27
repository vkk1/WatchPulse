from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any

from app.db.client import get_supabase_client


@dataclass
class ModelDayRaw:
    model_id: int
    captured_date: date
    msrp: float | None
    median_price: float
    listings_count: int
    new_listings_count: int
    sold_rate_proxy: float
    premium_over_msrp: float | None
    availability_ratio: float
    avg_shipping_days: float


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high == low:
        return [0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


def _wait_band(index: float) -> str:
    if index < 0.25:
        return "0-6 months"
    if index < 0.45:
        return "6-18 months"
    if index < 0.65:
        return "18 months-3 years"
    if index < 0.85:
        return "3-5 years"
    return "5-8+ years"


def _calc_model_raw(
    *,
    model_id: int,
    msrp: float | None,
    listing_rows: list[dict[str, Any]],
    snapshot_rows: list[dict[str, Any]],
    captured_date: date,
) -> ModelDayRaw | None:
    listing_ids = [row["id"] for row in listing_rows]
    if not listing_ids:
        return None

    snapshots = [row for row in snapshot_rows if row["listing_id"] in listing_ids]
    if not snapshots:
        return None

    prices = [float(row["price_value"]) for row in snapshots if row.get("price_value") is not None]
    if not prices:
        return None

    listings_count = len(snapshots)
    available_count = sum(1 for row in snapshots if bool(row.get("availability_flag")))
    availability_ratio = available_count / listings_count if listings_count else 0.0
    sold_rate_proxy = 1.0 - availability_ratio

    created_today = sum(
        1
        for row in listing_rows
        if row.get("created_at") and str(row["created_at"])[:10] == captured_date.isoformat()
    )

    shipping_values: list[float] = []
    for row in snapshots:
        s_min = row.get("shipping_days_min")
        s_max = row.get("shipping_days_max")
        if s_min is not None and s_max is not None:
            shipping_values.append((float(s_min) + float(s_max)) / 2.0)
    avg_shipping_days = sum(shipping_values) / len(shipping_values) if shipping_values else 7.0

    median_price = float(median(prices))
    premium_over_msrp = None
    if msrp and msrp > 0:
        premium_over_msrp = (median_price / float(msrp)) - 1.0

    return ModelDayRaw(
        model_id=model_id,
        captured_date=captured_date,
        msrp=msrp,
        median_price=median_price,
        listings_count=listings_count,
        new_listings_count=created_today,
        sold_rate_proxy=sold_rate_proxy,
        premium_over_msrp=premium_over_msrp,
        availability_ratio=availability_ratio,
        avg_shipping_days=avg_shipping_days,
    )


def _score_rows(rows: list[ModelDayRaw], *, w1: float = 0.45, w2: float = 0.30, w3: float = 0.25) -> list[dict[str, Any]]:
    premiums = [row.premium_over_msrp if row.premium_over_msrp is not None else 0.0 for row in rows]
    availability = [row.availability_ratio for row in rows]
    # Velocity proxy combines new listings churn and sold pressure.
    velocities = [
        0.6 * row.sold_rate_proxy + 0.4 * (row.new_listings_count / row.listings_count if row.listings_count else 0.0)
        for row in rows
    ]

    premium_norm = _normalize(premiums)
    availability_norm = _normalize(availability)
    velocity_norm = _normalize(velocities)

    scored: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        wait_time_index = (w1 * premium_norm[idx]) + (w2 * (1.0 - availability_norm[idx])) + (w3 * velocity_norm[idx])
        wait_time_index = max(0.0, min(1.0, wait_time_index))
        scored.append(
            {
                "model_id": row.model_id,
                "captured_date": row.captured_date.isoformat(),
                "median_price": round(row.median_price, 2),
                "listings_count": row.listings_count,
                "new_listings_count": row.new_listings_count,
                "sold_rate_proxy": round(row.sold_rate_proxy, 4),
                "premium_over_msrp": round(row.premium_over_msrp, 4) if row.premium_over_msrp is not None else None,
                "wait_time_index": round(wait_time_index, 4),
                "wait_band": _wait_band(wait_time_index),
            }
        )
    return scored


def compute_model_daily_stats(captured_date: date, brand: str = "rolex") -> list[dict[str, Any]]:
    client = get_supabase_client()

    models_response = (
        client.table("brand_models")
        .select("id,msrp")
        .eq("brand", brand)
        .order("id")
        .execute()
    )
    models = models_response.data or []
    if not models:
        return []

    model_ids = [row["id"] for row in models]
    listing_response = (
        client.table("market_listings")
        .select("id,model_id,created_at")
        .in_("model_id", model_ids)
        .execute()
    )
    listing_rows = listing_response.data or []
    if not listing_rows:
        return []

    listing_ids = [row["id"] for row in listing_rows]
    snapshot_response = (
        client.table("listing_snapshots")
        .select("listing_id,price_value,availability_flag,shipping_days_min,shipping_days_max")
        .eq("captured_date", captured_date.isoformat())
        .in_("listing_id", listing_ids)
        .execute()
    )
    snapshot_rows = snapshot_response.data or []
    if not snapshot_rows:
        return []

    listings_by_model: dict[int, list[dict[str, Any]]] = {}
    for row in listing_rows:
        listings_by_model.setdefault(int(row["model_id"]), []).append(row)

    raw_rows: list[ModelDayRaw] = []
    for model in models:
        model_id = int(model["id"])
        raw = _calc_model_raw(
            model_id=model_id,
            msrp=float(model["msrp"]) if model.get("msrp") is not None else None,
            listing_rows=listings_by_model.get(model_id, []),
            snapshot_rows=snapshot_rows,
            captured_date=captured_date,
        )
        if raw:
            raw_rows.append(raw)

    return _score_rows(raw_rows)


def upsert_model_daily_stats(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    client = get_supabase_client()
    client.table("model_daily_stats").upsert(rows, on_conflict="model_id,captured_date").execute()
    return len(rows)
