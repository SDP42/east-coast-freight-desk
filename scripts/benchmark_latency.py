"""Measure read-endpoint latency against a running API.

Usage (API running):  backend/.venv/bin/python scripts/benchmark_latency.py [base_url] [runs]
Reports the first (cold) request and then p50/p95/max over `runs` warm requests per endpoint, and
whether p95 meets the 200 ms target. Numbers include the local HTTP round trip."""

import statistics
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
TARGET_MS = 200
ENDPOINTS = [
    "/health", "/market/ticker", "/market/history/BPI?limit=500", "/market/regions", "/compatibility/matrix", "/haldia/summary", "/map/overview",
    "/forecast/BPI?horizon=14", "/forecast-multi/BPI", "/signals/transfer", "/signals/berth-slots?port=Paradip", "/signals/demand",
    "/signals/cyclone?port=Haldia&laycan_start=2026-10-20&laycan_end=2026-11-05&transit_days=20", "/data/query?index_name=BPI&limit=200", "/risk/events",
    "/lab/chokepoints", "/lab/terrain", "/lab/models", "/forecast-deep/BPI", "/lab/fan/BPI?horizon=60", "/lab/lightering?cargo_tonnes=150000", "/briefing",
]


def main() -> None:
    client = httpx.Client(timeout=120)
    # Endpoints are permission-protected; benchmark as the demo administrator (needs scripts/seed_demo_users.py).
    token = client.post(BASE + "/auth/demo-login", json={"email": "admin@demo.example.com"}).json().get("access_token")
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"{'endpoint':<84}{'cold ms':>9}{'p50':>8}{'p95':>8}{'max':>8}  target")
    worst = 0.0
    for path in ENDPOINTS:
        t = time.perf_counter()
        r = client.get(BASE + path)
        cold = (time.perf_counter() - t) * 1000
        if r.status_code != 200:
            print(f"{path[:82]:<84}  HTTP {r.status_code}")
            continue
        samples = []
        for _ in range(RUNS):
            t = time.perf_counter()
            client.get(BASE + path)
            samples.append((time.perf_counter() - t) * 1000)
        samples.sort()
        p95 = samples[int(len(samples) * 0.95) - 1]
        worst = max(worst, p95)
        print(f"{path[:82]:<84}{cold:>9.0f}{statistics.median(samples):>8.1f}{p95:>8.1f}{samples[-1]:>8.1f}  {'PASS' if p95 <= TARGET_MS else 'FAIL'}")
    print(f"\nWorst warm p95: {worst:.1f} ms (target {TARGET_MS} ms)")


if __name__ == "__main__":
    main()
