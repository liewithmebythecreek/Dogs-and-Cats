"""
Background Prometheus collector for continuous model-drift checks.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import traceback

import numpy as np
from prometheus_client import Counter, Gauge

from app.services.drift_utils import (
    CITY_NAMES,
    DEFAULT_DRIFT_DAYS,
    DEFAULT_THRESHOLD_C,
    compute_mae,
    fetch_actuals,
    load_forecast_log,
)


DRIFT_CITY_MAE = Gauge(
    "weather_model_drift_city_mae_celsius",
    "MAE in Celsius for each city in the drift window.",
    ["city"],
)
DRIFT_OVERALL_MAE = Gauge(
    "weather_model_drift_overall_mae_celsius",
    "Overall MAE in Celsius across all cities.",
)
DRIFT_THRESHOLD = Gauge(
    "weather_model_drift_threshold_celsius",
    "Configured MAE threshold in Celsius used to declare drift.",
)
DRIFT_DETECTED = Gauge(
    "weather_model_drift_detected",
    "1 when overall MAE is above threshold, else 0.",
)
DRIFT_LAST_CHECK_TS = Gauge(
    "weather_model_drift_last_check_timestamp_seconds",
    "Unix timestamp of the last drift check attempt.",
)
DRIFT_LAST_CHECK_DURATION = Gauge(
    "weather_model_drift_last_check_duration_seconds",
    "Duration in seconds of the last drift check attempt.",
)
DRIFT_LAST_CHECK_STATUS = Gauge(
    "weather_model_drift_last_check_status",
    "Status code of the last drift check (0=success,1=insufficient_data,2=error).",
)
DRIFT_PREDICTION_SAMPLES = Gauge(
    "weather_model_drift_prediction_samples",
    "Number of prediction samples available for each city.",
    ["city"],
)
DRIFT_ACTUAL_SAMPLES = Gauge(
    "weather_model_drift_actual_samples",
    "Number of actual observation samples available for each city.",
    ["city"],
)
DRIFT_CHECK_TOTAL = Counter(
    "weather_model_drift_check_total",
    "Total number of drift checks grouped by outcome.",
    ["status"],
)


def _env_as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


def _env_as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class DriftPrometheusMonitor:
    def __init__(
        self,
        *,
        enabled: bool,
        interval_seconds: int,
        days: int,
        threshold_c: float,
    ) -> None:
        self.enabled = enabled
        self.interval_seconds = interval_seconds
        self.days = days
        self.threshold_c = threshold_c
        self._task: asyncio.Task | None = None

    @classmethod
    def from_env(cls) -> "DriftPrometheusMonitor":
        return cls(
            enabled=_env_as_bool("ENABLE_DRIFT_MONITORING", True),
            interval_seconds=_env_as_int("DRIFT_CHECK_INTERVAL_SECONDS", 900),
            days=_env_as_int("DRIFT_LOOKBACK_DAYS", DEFAULT_DRIFT_DAYS),
            threshold_c=_env_as_float("DRIFT_MAE_THRESHOLD_C", DEFAULT_THRESHOLD_C),
        )

    async def start(self) -> None:
        if not self.enabled:
            print("[prometheus_drift] Continuous drift checks are disabled.")
            return
        if self._task and not self._task.done():
            return
        print(
            "[prometheus_drift] Starting monitor "
            f"(every {self.interval_seconds}s, window={self.days}d, threshold={self.threshold_c}C)."
        )
        self._task = asyncio.create_task(self._run_loop(), name="drift_prometheus_monitor")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        print("[prometheus_drift] Monitor stopped.")

    async def _run_loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                print("[prometheus_drift] Drift check failed with unexpected error:")
                traceback.print_exc()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        started_at = dt.datetime.now(dt.timezone.utc)
        DRIFT_THRESHOLD.set(self.threshold_c)
        DRIFT_LAST_CHECK_TS.set(started_at.timestamp())

        try:
            actuals = await fetch_actuals(self.days)
            predictions = load_forecast_log(self.days)

            for city in CITY_NAMES:
                DRIFT_ACTUAL_SAMPLES.labels(city=city).set(len(actuals.get(city, [])))
                DRIFT_PREDICTION_SAMPLES.labels(city=city).set(len(predictions.get(city, [])))

            if not any(predictions.get(city) for city in CITY_NAMES):
                self._mark_insufficient_data("No predictions available in forecast log window.")
                return

            mae_by_city = compute_mae(actuals, predictions)
            if not mae_by_city:
                self._mark_insufficient_data("No overlapping samples to compute MAE.")
                return

            for city in CITY_NAMES:
                DRIFT_CITY_MAE.labels(city=city).set(mae_by_city.get(city, 0.0))

            overall_mae = float(np.mean(list(mae_by_city.values())))
            is_drift = overall_mae > self.threshold_c

            DRIFT_OVERALL_MAE.set(overall_mae)
            DRIFT_DETECTED.set(1.0 if is_drift else 0.0)
            DRIFT_LAST_CHECK_STATUS.set(0)
            DRIFT_CHECK_TOTAL.labels(status="success").inc()

            print(
                "[prometheus_drift] success "
                f"(overall_mae={overall_mae:.3f}C, threshold={self.threshold_c:.3f}C, drift={is_drift})."
            )
        except Exception:
            DRIFT_LAST_CHECK_STATUS.set(2)
            DRIFT_CHECK_TOTAL.labels(status="error").inc()
            DRIFT_OVERALL_MAE.set(-1.0)
            DRIFT_DETECTED.set(0.0)
            raise
        finally:
            finished_at = dt.datetime.now(dt.timezone.utc)
            DRIFT_LAST_CHECK_DURATION.set((finished_at - started_at).total_seconds())
            DRIFT_LAST_CHECK_TS.set(finished_at.timestamp())

    def _mark_insufficient_data(self, reason: str) -> None:
        DRIFT_LAST_CHECK_STATUS.set(1)
        DRIFT_CHECK_TOTAL.labels(status="insufficient_data").inc()
        DRIFT_OVERALL_MAE.set(-1.0)
        DRIFT_DETECTED.set(0.0)
        for city in CITY_NAMES:
            DRIFT_CITY_MAE.labels(city=city).set(0.0)
        print(f"[prometheus_drift] insufficient_data ({reason})")


drift_monitor = DriftPrometheusMonitor.from_env()

