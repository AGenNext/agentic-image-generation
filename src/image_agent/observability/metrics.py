"""Prometheus metrics for image operations with a dependency-light fallback."""

from __future__ import annotations

import importlib
import importlib.util

_PROM_SPEC = importlib.util.find_spec("prometheus_client")

if _PROM_SPEC is not None:
    _prom = importlib.import_module("prometheus_client")
    CollectorRegistry = _prom.CollectorRegistry
    CONTENT_TYPE_LATEST = _prom.CONTENT_TYPE_LATEST
    generate_latest = _prom.generate_latest

    def Counter(name: str, description: str, labels: list[str] | tuple[str, ...], registry: object):
        return _prom.Counter(name, description, labels, registry=registry)

    def Histogram(name: str, description: str, labels: list[str] | tuple[str, ...], buckets: tuple[float, ...], registry: object):
        return _prom.Histogram(name, description, labels, buckets=buckets, registry=registry)
else:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _Metric:
        def __init__(self, name: str, description: str, labels: list[str] | tuple[str, ...] = (), **_: object) -> None:
            self.name = name
            self.description = description
            self.values: dict[tuple[str, ...], float] = {}

        def labels(self, *values: object) -> "_Metric":
            self._current = tuple(str(v) for v in values)
            self.values.setdefault(self._current, 0.0)
            return self

        def inc(self, amount: float = 1.0) -> None:
            key = getattr(self, "_current", ())
            self.values[key] = self.values.get(key, 0.0) + amount

        def observe(self, amount: float) -> None:
            self.inc(amount)

    class CollectorRegistry:
        def __init__(self) -> None:
            self.metrics: list[_Metric] = []

    def Counter(name: str, description: str, labels: list[str] | tuple[str, ...], registry: CollectorRegistry) -> _Metric:
        metric = _Metric(name, description, labels)
        registry.metrics.append(metric)
        return metric

    def Histogram(name: str, description: str, labels: list[str] | tuple[str, ...], buckets: tuple[float, ...], registry: CollectorRegistry) -> _Metric:
        metric = _Metric(name, description, labels)
        registry.metrics.append(metric)
        return metric

    def generate_latest(registry: CollectorRegistry) -> bytes:
        lines: list[str] = []
        for metric in registry.metrics:
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} counter")
            for labels, value in metric.values.items():
                suffix = "" if not labels else "{" + ",".join(f'l{i}=\"{label}\"' for i, label in enumerate(labels)) + "}"
                lines.append(f"{metric.name}{suffix} {value}")
        return ("\n".join(lines) + "\n").encode()

registry = CollectorRegistry()
image_operations_total = Counter("image_operations_total", "Image operations by endpoint, tenant, and status", ["endpoint", "tenant", "status"], registry=registry)
image_bytes_total = Counter("image_bytes_total", "Bytes processed by direction and format", ["direction", "format"], registry=registry)
image_operation_latency_seconds = Histogram("image_operation_latency_seconds", "Image operation latency", ["endpoint"], buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5), registry=registry)
image_cost_usd_total = Counter("image_cost_usd_total", "Estimated per-operation cost in USD", ["tenant"], registry=registry)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(registry), CONTENT_TYPE_LATEST
