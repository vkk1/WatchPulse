from datetime import date

from app.services.wait_time import _calc_model_raw, _score_rows


def test_median_price_and_premium_exact():
    captured = date(2026, 2, 26)
    listing_rows = [
        {"id": 1, "created_at": "2026-02-26T10:00:00+00:00"},
        {"id": 2, "created_at": "2026-02-25T10:00:00+00:00"},
        {"id": 3, "created_at": "2026-02-26T12:00:00+00:00"},
    ]
    snapshot_rows = [
        {"listing_id": 1, "price_value": 9000, "availability_flag": True, "shipping_days_min": 2, "shipping_days_max": 4},
        {"listing_id": 2, "price_value": 10000, "availability_flag": True, "shipping_days_min": 2, "shipping_days_max": 4},
        {"listing_id": 3, "price_value": 11000, "availability_flag": False, "shipping_days_min": 3, "shipping_days_max": 5},
    ]

    raw = _calc_model_raw(
        model_id=99,
        msrp=10000.0,
        listing_rows=listing_rows,
        snapshot_rows=snapshot_rows,
        captured_date=captured,
    )

    assert raw is not None
    assert raw.median_price == 10000.0          # exact median of [9000,10000,11000]
    assert raw.premium_over_msrp == 0.0         # (10000 / 10000) - 1


def test_wait_time_index_sanity_high_premium_low_availability_is_higher():
    captured = date(2026, 2, 26)

    # Scarce model: high premium and low availability.
    scarce_listing_rows = [{"id": i, "created_at": "2026-02-25T10:00:00+00:00"} for i in range(1, 5)]
    scarce_snapshot_rows = [
        {"listing_id": 1, "price_value": 15000, "availability_flag": False, "shipping_days_min": 7, "shipping_days_max": 12},
        {"listing_id": 2, "price_value": 15200, "availability_flag": False, "shipping_days_min": 8, "shipping_days_max": 12},
        {"listing_id": 3, "price_value": 14900, "availability_flag": False, "shipping_days_min": 7, "shipping_days_max": 11},
        {"listing_id": 4, "price_value": 15100, "availability_flag": True, "shipping_days_min": 6, "shipping_days_max": 10},
    ]

    # Common model: near MSRP and high availability.
    common_listing_rows = [{"id": i, "created_at": "2026-02-25T10:00:00+00:00"} for i in range(11, 15)]
    common_snapshot_rows = [
        {"listing_id": 11, "price_value": 9900, "availability_flag": True, "shipping_days_min": 1, "shipping_days_max": 3},
        {"listing_id": 12, "price_value": 10100, "availability_flag": True, "shipping_days_min": 1, "shipping_days_max": 3},
        {"listing_id": 13, "price_value": 10000, "availability_flag": True, "shipping_days_min": 1, "shipping_days_max": 2},
        {"listing_id": 14, "price_value": 10050, "availability_flag": True, "shipping_days_min": 2, "shipping_days_max": 3},
    ]

    scarce_raw = _calc_model_raw(
        model_id=1,
        msrp=10000.0,
        listing_rows=scarce_listing_rows,
        snapshot_rows=scarce_snapshot_rows,
        captured_date=captured,
    )
    common_raw = _calc_model_raw(
        model_id=2,
        msrp=10000.0,
        listing_rows=common_listing_rows,
        snapshot_rows=common_snapshot_rows,
        captured_date=captured,
    )

    assert scarce_raw is not None and common_raw is not None
    scored = _score_rows([scarce_raw, common_raw])
    by_model = {row["model_id"]: row for row in scored}

    assert scarce_raw.premium_over_msrp > common_raw.premium_over_msrp
    assert scarce_raw.availability_ratio < common_raw.availability_ratio
    assert by_model[1]["wait_time_index"] > by_model[2]["wait_time_index"]
