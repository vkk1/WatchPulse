# Query Tuning Notes (Week 4)

Use this SQL in Supabase SQL editor to simplify query shapes and improve `/v1/models` latency.

## 1) Fast path for latest stats per model

```sql
create or replace view public.model_latest_stats as
select distinct on (mds.model_id)
  mds.model_id,
  mds.captured_date,
  mds.median_price,
  mds.wait_band,
  mds.wait_time_index,
  mds.premium_over_msrp,
  mds.listings_count,
  mds.new_listings_count,
  mds.sold_rate_proxy
from public.model_daily_stats mds
order by mds.model_id, mds.captured_date desc;
```

This supports one-row-per-model reads without scanning all model history in API code.

## 2) Indexes for list endpoint and latest-stats reads

```sql
-- Already useful for latest row access by model.
create index if not exists ix_mds_model_date_desc
  on public.model_daily_stats (model_id, captured_date desc);

-- Optional covering index for latest-stats lookups.
create index if not exists ix_mds_model_date_desc_cover
  on public.model_daily_stats (model_id, captured_date desc)
  include (median_price, wait_band, wait_time_index, premium_over_msrp, listings_count, new_listings_count, sold_rate_proxy);

-- Supports ordered list browse on brand + collection + name.
create index if not exists ix_brand_models_browse
  on public.brand_models (brand, collection, model_name, id);
```

## 3) Search tuning for `ILIKE '%q%'`

If search volume grows, trigram indexes avoid full scans:

```sql
create extension if not exists pg_trgm;

create index if not exists ix_brand_models_model_name_trgm
  on public.brand_models using gin (model_name gin_trgm_ops);

create index if not exists ix_brand_models_ref_code_trgm
  on public.brand_models using gin (ref_code gin_trgm_ops);
```

## 4) EXPLAIN checks

Run these before/after adding indexes and compare costs/timing.

```sql
explain analyze
select id, brand, collection, model_name, ref_code, msrp, image_url
from public.brand_models
where brand = 'rolex'
order by collection, model_name
limit 25 offset 0;

explain analyze
select model_id, median_price, wait_band, wait_time_index
from public.model_latest_stats
where model_id in (1,2,3,4,5,6,7,8,9,10);
```
