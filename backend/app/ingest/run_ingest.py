from __future__ import annotations

import argparse
from datetime import date, datetime

from app.ingest.validate import run_ingest_validations
from app.services.wait_time import compute_model_daily_stats, upsert_model_daily_stats


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def run(brand: str, captured_date: date, anomaly_threshold_pct: float) -> tuple[int, dict]:
    rows = compute_model_daily_stats(captured_date=captured_date, brand=brand)
    upserted = upsert_model_daily_stats(rows)
    validation = run_ingest_validations(
        brand=brand,
        captured_date=captured_date,
        anomaly_threshold_pct=anomaly_threshold_pct,
    )
    return upserted, validation.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute and upsert daily model stats.")
    parser.add_argument("--brand", default="rolex", help="Brand to process (default: rolex)")
    parser.add_argument("--date", default=None, help="Capture date in YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--anomaly-threshold-pct",
        type=float,
        default=25.0,
        help="Flag listing snapshot day-over-day jumps above this percentage (default: 25)",
    )
    args = parser.parse_args()

    captured_date = _parse_date(args.date)
    inserted, validation = run(
        brand=args.brand.lower(),
        captured_date=captured_date,
        anomaly_threshold_pct=float(args.anomaly_threshold_pct),
    )
    print(f"Upserted {inserted} model_daily_stats rows for {args.brand.lower()} on {captured_date.isoformat()}")
    print(
        "Validation summary: "
        f"anomalies={validation['anomaly_count']} "
        f"missing_stats={validation['missing_stats_count']} "
        f"duplicate_urls={validation['duplicate_url_count']}"
    )
    if validation["anomaly_examples"]:
        print(f"Anomaly sample: {validation['anomaly_examples'][:3]}")
    if validation["missing_stats_model_ids"]:
        print(f"Missing model_ids sample: {validation['missing_stats_model_ids'][:10]}")
    if validation["duplicate_url_examples"]:
        print(f"Duplicate URL sample: {validation['duplicate_url_examples'][:3]}")


if __name__ == "__main__":
    main()
