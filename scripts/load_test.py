"""Fires N concurrent requests at ModeraAI to demo scaling (topic 1) and
rate limiting (topic 9, by pointing TARGET_URL at the API Gateway URL instead).

Usage:
    uv run python scripts/load_test.py                                     # 50 concurrent requests against SERVICE_URL
    uv run python scripts/load_test.py --url "$GATEWAY_URL" --requests 15  # API_KEY is read from the environment
"""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SAMPLE_TEXTS = [
    "Great article, thanks for sharing!",
    "I disagree with this policy.",
    "This is the worst thing I've ever read.",
    "Can someone explain how this works?",
    "I hate you, you're so stupid and ugly",
]


def fire_one(url: str, index: int, api_key: str | None):
    text = SAMPLE_TEXTS[index % len(SAMPLE_TEXTS)] + f" (request #{index})"
    params = {"key": api_key} if api_key else None
    start = time.time()
    try:
        resp = requests.post(f"{url}/moderate", json={"text": text}, params=params, timeout=30)
        elapsed = time.time() - start
        return index, resp.status_code, round(elapsed, 2)
    except requests.RequestException as exc:
        elapsed = time.time() - start
        return index, f"ERROR: {exc}", round(elapsed, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("SERVICE_URL", "https://moderaai-1039893753206.us-central1.run.app"))
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--workers", type=int, default=50)
    parser.add_argument("--api-key", default=os.environ.get("API_KEY"), help="Required when --url points at the API Gateway URL (topic 9)")
    args = parser.parse_args()

    print(f"Firing {args.requests} concurrent requests at {args.url} ...\n")

    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(fire_one, args.url, i, args.api_key) for i in range(args.requests)]
        for future in as_completed(futures):
            results.append(future.result())
    total_time = round(time.time() - start, 2)

    results.sort(key=lambda r: r[0])
    for index, status, elapsed in results:
        print(f"  request #{index:>3}  status={status}  time={elapsed}s")

    ok = sum(1 for _, status, _ in results if status == 200)
    rejected = sum(1 for _, status, _ in results if status == 429)
    print(f"\n{ok}/{len(results)} succeeded, {rejected} rejected with 429, total wall time: {total_time}s")


if __name__ == "__main__":
    main()
