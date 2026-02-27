from __future__ import annotations

import argparse
from datetime import date, datetime

from app.services.wait_time import compute_model_daily_stats, upsert_model_daily_stats


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def run(brand: str, captured_date: date) -> int:
    rows = compute_model_daily_stats(captured_date=captured_date, brand=brand)
    return upsert_model_daily_stats(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute and upsert daily model stats.")
    parser.add_argument("--brand", default="rolex", help="Brand to process (default: rolex)")
    parser.add_argument("--date", default=None, help="Capture date in YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    captured_date = _parse_date(args.date)
    inserted = run(brand=args.brand.lower(), captured_date=captured_date)
    print(f"Upserted {inserted} model_daily_stats rows for {args.brand.lower()} on {captured_date.isoformat()}")


if __name__ == "__main__":
    main()
