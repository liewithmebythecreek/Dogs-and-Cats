"""
CLI drift detector.

Compares logged model predictions against recent Open-Meteo observations and exits with:
  0 => no drift detected
  1 => drift detected
  2 => insufficient data / fetch failure

Usage:
  python -m backend.monitor
  python -m backend.monitor --threshold 1.5 --days 7
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.drift_utils import (  # noqa: E402
    CITY_NAMES,
    DEFAULT_DRIFT_DAYS,
    DEFAULT_THRESHOLD_C,
    FORECAST_LOG_PATH,
    compute_mae,
    fetch_actuals,
    load_forecast_log,
)


async def main(threshold: float, days: int) -> None:
    print(f"[monitor] Drift detection window={days} day(s), threshold={threshold}C")
    print(f"[monitor] Forecast log path: {FORECAST_LOG_PATH}")

    print("[monitor] Fetching actuals...")
    try:
        actuals = await fetch_actuals(days)
    except Exception as exc:
        print(f"[monitor] Failed to fetch actuals: {exc}", file=sys.stderr)
        sys.exit(2)

    print("[monitor] Loading predictions from forecast log...")
    predictions = load_forecast_log(days)
    if not any(len(values) > 0 for values in predictions.values()):
        print("[monitor] No prediction entries in window; cannot evaluate drift.", file=sys.stderr)
        sys.exit(2)

    mae_by_city = compute_mae(actuals, predictions)
    if not mae_by_city:
        print("[monitor] No overlapping samples to compute MAE.", file=sys.stderr)
        sys.exit(2)

    print("\n[monitor] Drift report")
    print(f"{'City':<14} {'MAE (C)':>10}  Status")
    print("-" * 36)

    for city in CITY_NAMES:
        if city not in mae_by_city:
            print(f"{city:<14} {'n/a':>10}  insufficient-data")
            continue
        err = mae_by_city[city]
        status = "DRIFT" if err > threshold else "ok"
        print(f"{city:<14} {err:>10.2f}  {status}")

    overall_mae = float(np.mean(list(mae_by_city.values())))
    overall_status = "DRIFT_DETECTED" if overall_mae > threshold else "NO_DRIFT"
    print("-" * 36)
    print(f"{'OVERALL':<14} {overall_mae:>10.2f}  {overall_status}")

    if overall_mae > threshold:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STGNN Drift Detector")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD_C,
        help="MAE threshold above which drift is declared (default: 2.0)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DRIFT_DAYS,
        help="Number of past days to evaluate (default: 7)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.threshold, args.days))

