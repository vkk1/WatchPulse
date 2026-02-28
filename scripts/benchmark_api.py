from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class Sample:
    latency_ms: float
    status_code: int
    ok: bool
    bytes_len: int
    error: str | None = None


@dataclass
class TaskResult:
    final_sample: Sample
    attempts: int


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    p = max(0.0, min(100.0, p))
    k = (len(values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1


def hit_once(base_url: str, page_size: int, timeout_sec: float, vary_params: bool, seed: int | None) -> Sample:
    params = {"page": 1, "page_size": page_size}
    if vary_params:
        rng = random.Random(seed if seed is not None else time.time_ns())
        params["page"] = rng.randint(1, 3)
        params["q"] = rng.choice(["", "Datejust", "Daytona", "116", "126"])
        params["collection"] = rng.choice(["", "Datejust", "Submariner", "GMT-Master II", "Day-Date"])

    query = urlencode(params)
    url = f"{base_url.rstrip('/')}/v1/models?{query}"
    request = Request(url, method="GET")
    request.add_header("Accept", "application/json")

    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            body = response.read()
            latency = (time.perf_counter() - started) * 1000
            status = int(getattr(response, "status", 200))
            return Sample(latency_ms=latency, status_code=status, ok=200 <= status < 300, bytes_len=len(body))
    except HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000
        return Sample(latency_ms=latency, status_code=int(exc.code), ok=False, bytes_len=0, error=str(exc))
    except (URLError, TimeoutError, OSError) as exc:
        latency = (time.perf_counter() - started) * 1000
        return Sample(latency_ms=latency, status_code=0, ok=False, bytes_len=0, error=str(exc))


def hit_with_retries(
    *,
    base_url: str,
    page_size: int,
    timeout_sec: float,
    vary_params: bool,
    seed: int,
    max_retries: int,
    retry_backoff_ms: int,
) -> TaskResult:
    attempts = 0
    last = Sample(latency_ms=0.0, status_code=0, ok=False, bytes_len=0, error="No attempts")
    for attempt in range(max_retries + 1):
        attempts += 1
        sample = hit_once(base_url, page_size, timeout_sec, vary_params, seed + attempt)
        if sample.ok:
            return TaskResult(final_sample=sample, attempts=attempts)
        last = sample
        if attempt < max_retries:
            time.sleep(max(0, retry_backoff_ms) / 1000.0)
    return TaskResult(final_sample=last, attempts=attempts)


def run_benchmark(
    base_url: str,
    requests_count: int,
    concurrency: int,
    page_size: int,
    timeout_sec: float,
    warmup: int,
    vary_params: bool,
    max_retries: int,
    retry_backoff_ms: int,
) -> dict[str, Any]:
    for i in range(max(0, warmup)):
        _ = hit_once(base_url, page_size, timeout_sec, vary_params=False, seed=i)

    samples: list[Sample] = []
    total_attempts = 0
    started_at = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(
                hit_with_retries,
                base_url=base_url,
                page_size=page_size,
                timeout_sec=timeout_sec,
                vary_params=vary_params,
                seed=i,
                max_retries=max_retries,
                retry_backoff_ms=retry_backoff_ms,
            )
            for i in range(requests_count)
        ]
        for fut in as_completed(futures):
            result = fut.result()
            samples.append(result.final_sample)
            total_attempts += result.attempts

    total_duration_sec = max(time.perf_counter() - started_at, 1e-9)

    latencies = sorted(s.latency_ms for s in samples)
    ok_samples = [s for s in samples if s.ok]
    error_samples = [s for s in samples if not s.ok]

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    avg = statistics.fmean(latencies) if latencies else 0.0
    throughput = len(samples) / total_duration_sec

    status_counts: dict[str, int] = {}
    for s in samples:
        key = str(s.status_code)
        status_counts[key] = status_counts.get(key, 0) + 1

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "endpoint": "/v1/models",
        "requests": requests_count,
        "concurrency": concurrency,
        "page_size": page_size,
        "warmup_requests": warmup,
        "vary_params": vary_params,
        "max_retries": max_retries,
        "retry_backoff_ms": retry_backoff_ms,
        "total_attempts": total_attempts,
        "total_duration_sec": round(total_duration_sec, 4),
        "throughput_rps": round(throughput, 2),
        "latency_ms": {
            "avg": round(avg, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "min": round(min(latencies) if latencies else 0.0, 2),
            "max": round(max(latencies) if latencies else 0.0, 2),
        },
        "success_count": len(ok_samples),
        "error_count": len(error_samples),
        "status_counts": status_counts,
        "errors_sample": [s.error for s in error_samples[:5] if s.error],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark /v1/models latency and report p50/p95.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--requests", type=int, default=300, help="Total request count")
    parser.add_argument("--concurrency", type=int, default=20, help="Parallel workers")
    parser.add_argument("--page-size", type=int, default=25, help="page_size query param")
    parser.add_argument("--timeout-sec", type=float, default=10.0, help="Per-request timeout")
    parser.add_argument("--warmup", type=int, default=20, help="Warmup request count")
    parser.add_argument("--vary-params", action="store_true", help="Vary query params across requests")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries per logical request on failure")
    parser.add_argument("--retry-backoff-ms", type=int, default=50, help="Backoff between retries in milliseconds")
    parser.add_argument("--output", default="", help="Optional JSON file output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    report = run_benchmark(
        base_url=args.base_url,
        requests_count=max(1, args.requests),
        concurrency=max(1, args.concurrency),
        page_size=max(1, args.page_size),
        timeout_sec=max(0.1, args.timeout_sec),
        warmup=max(0, args.warmup),
        vary_params=bool(args.vary_params),
        max_retries=max(0, args.max_retries),
        retry_backoff_ms=max(0, args.retry_backoff_ms),
    )

    print("Benchmark complete")
    print(f"Endpoint: {report['base_url']}{report['endpoint']}")
    print(f"Requests: {report['requests']} | Concurrency: {report['concurrency']} | Warmup: {report['warmup_requests']}")
    print(f"Success: {report['success_count']} | Errors: {report['error_count']} | Throughput: {report['throughput_rps']} rps")
    print(
        f"Retries: max={report['max_retries']} backoff_ms={report['retry_backoff_ms']} "
        f"| total_attempts={report['total_attempts']}"
    )
    print(
        "Latency (ms): "
        f"avg={report['latency_ms']['avg']} "
        f"p50={report['latency_ms']['p50']} "
        f"p95={report['latency_ms']['p95']} "
        f"min={report['latency_ms']['min']} "
        f"max={report['latency_ms']['max']}"
    )
    print(f"Status counts: {report['status_counts']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Saved report: {args.output}")


if __name__ == "__main__":
    main()
