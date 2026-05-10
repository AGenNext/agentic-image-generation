"""Per-operation image cost attribution utilities."""

from __future__ import annotations

from dataclasses import dataclass

BYTES_PER_GB = 1024 ** 3
SECONDS_PER_MONTH = 30 * 24 * 60 * 60


@dataclass(frozen=True)
class CostRates:
    storage_gb_month_usd: float = 0.023
    cpu_second_usd: float = 0.000011
    bandwidth_gb_usd: float = 0.09


def estimate_operation_cost(
    *,
    input_bytes: int,
    output_bytes: int,
    processing_time_ms: int,
    rates: CostRates | None = None,
) -> dict[str, float]:
    rates = rates or CostRates()
    storage_gb_seconds = (output_bytes / BYTES_PER_GB) * processing_time_ms / 1000
    storage_cost = storage_gb_seconds * rates.storage_gb_month_usd / SECONDS_PER_MONTH
    cpu_cost = (processing_time_ms / 1000) * rates.cpu_second_usd
    bandwidth_cost = ((input_bytes + output_bytes) / BYTES_PER_GB) * rates.bandwidth_gb_usd
    total = storage_cost + cpu_cost + bandwidth_cost
    return {
        "storage_usd": round(storage_cost, 8),
        "cpu_usd": round(cpu_cost, 8),
        "bandwidth_usd": round(bandwidth_cost, 8),
        "total_usd": round(total, 8),
    }
