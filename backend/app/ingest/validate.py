from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from app.db.client import get_supabase_client


@dataclass
class ValidationReport:
    captured_date: str
    brand: str
    anomaly_threshold_pct: float
    anomaly_count: int
    anomaly_examples: list[dict[str, Any]]
    missing_stats_count: int
    missing_stats_model_ids: list[int]
    duplicate_url_count: int
    duplicate_url_examples: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_brand_model_ids(brand: str) -> list[int]:
    client = get_supabase_client()
    response = client.table("brand_models").select("id").eq("brand", brand).execute()
    return [int(row["id"]) for row in (response.data or [])]


def _check_duplicate_urls(model_ids: list[int]) -> tuple[int, list[dict[str, Any]]]:
    if not model_ids:
        return 0, []
    client = get_supabase_client()
    response = client.table("market_listings").select("url").in_("model_id", model_ids).execute()
    seen: dict[str, int] = {}
    for row in (response.data or []):
        url = str(row.get("url") or "").strip()
        if not url:
            continue
        seen[url] = seen.get(url, 0) + 1

    duplicates = [{"url": url, "count": count} for url, count in seen.items() if count > 1]
    duplicates.sort(key=lambda x: x["count"], reverse=True)
    return len(duplicates), duplicates[:10]


def _check_missing_stats(model_ids: list[int], captured_date: date) -> tuple[int, list[int]]:
    if not model_ids:
        return 0, []
    client = get_supabase_client()
    response = (
        client.table("model_daily_stats")
        .select("model_id")
        .eq("captured_date", captured_date.isoformat())
        .in_("model_id", model_ids)
        .execute()
    )
    present = {int(row["model_id"]) for row in (response.data or [])}
    missing = sorted(mid for mid in model_ids if mid not in present)
    return len(missing), missing


def _check_price_anomalies(
    model_ids: list[int],
    captured_date: date,
    threshold_pct: float,
) -> tuple[int, list[dict[str, Any]]]:
    if not model_ids:
        return 0, []

    client = get_supabase_client()
    listings_res = client.table("market_listings").select("id").in_("model_id", model_ids).execute()
    listing_ids = [int(row["id"]) for row in (listings_res.data or [])]
    if not listing_ids:
        return 0, []

    prev_date = captured_date - timedelta(days=1)
    snapshots_res = (
        client.table("listing_snapshots")
        .select("listing_id,captured_date,price_value")
        .in_("listing_id", listing_ids)
        .in_("captured_date", [prev_date.isoformat(), captured_date.isoformat()])
        .execute()
    )

    prev_prices: dict[int, float] = {}
    curr_prices: dict[int, float] = {}
    for row in (snapshots_res.data or []):
        listing_id = int(row["listing_id"])
        value = row.get("price_value")
        if value is None:
            continue
        price = float(value)
        date_s = str(row.get("captured_date"))
        if date_s == prev_date.isoformat():
            prev_prices[listing_id] = price
        elif date_s == captured_date.isoformat():
            curr_prices[listing_id] = price

    anomalies: list[dict[str, Any]] = []
    for listing_id, curr in curr_prices.items():
        prev = prev_prices.get(listing_id)
        if prev is None or prev <= 0:
            continue
        pct_jump = abs((curr - prev) / prev) * 100.0
        if pct_jump > threshold_pct:
            anomalies.append(
                {
                    "listing_id": listing_id,
                    "prev_price": round(prev, 2),
                    "curr_price": round(curr, 2),
                    "pct_jump": round(pct_jump, 2),
                }
            )
    anomalies.sort(key=lambda x: x["pct_jump"], reverse=True)
    return len(anomalies), anomalies[:10]


def run_ingest_validations(
    *,
    brand: str,
    captured_date: date,
    anomaly_threshold_pct: float = 25.0,
) -> ValidationReport:
    model_ids = _get_brand_model_ids(brand)
    duplicate_count, duplicate_examples = _check_duplicate_urls(model_ids)
    missing_count, missing_model_ids = _check_missing_stats(model_ids, captured_date)
    anomaly_count, anomaly_examples = _check_price_anomalies(model_ids, captured_date, anomaly_threshold_pct)

    return ValidationReport(
        captured_date=captured_date.isoformat(),
        brand=brand,
        anomaly_threshold_pct=anomaly_threshold_pct,
        anomaly_count=anomaly_count,
        anomaly_examples=anomaly_examples,
        missing_stats_count=missing_count,
        missing_stats_model_ids=missing_model_ids,
        duplicate_url_count=duplicate_count,
        duplicate_url_examples=duplicate_examples,
    )
