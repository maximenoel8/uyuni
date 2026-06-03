# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/metrics_collector_handler.rb.

Provides MetricsCollector: pushes Prometheus gauges to a push gateway.
"""

try:
    from prometheus_client import Gauge, CollectorRegistry, push_to_gateway
except ImportError:  # optional dependency — not available in all environments
    Gauge = CollectorRegistry = push_to_gateway = None  # type: ignore[assignment,misc]


class MetricsCollector:
    def __init__(self, url="http://nsa.mgr.suse.de:9091"):
        self._url = url
        self._registry = CollectorRegistry() if CollectorRegistry is not None else None
        self._gauges = {}

    def push_metrics(self, job_name: str, metric_name: str,
                     metric_value: float, labels: dict = None):
        """
        Push a metric to the Metrics Collector.

        :param job_name: the job name to push the metric to
        :param metric_name: the metric name to push
        :param metric_value: the metric value to push
        :param labels: optional dict of label name → value
        :raises Exception: re-raises if push_to_gateway fails
        """
        if labels is None:
            labels = {}
        if Gauge is None or push_to_gateway is None:
            raise RuntimeError(
                "prometheus_client is not installed. "
                "Add prometheus-client>=0.20 to the project dependencies.")
        label_names = list(labels.keys())
        key = (metric_name, tuple(label_names))
        if key not in self._gauges:
            self._gauges[key] = Gauge(
                metric_name, metric_name,
                labelnames=label_names, registry=self._registry)
        self._gauges[key].labels(**labels).set(metric_value)
        try:
            push_to_gateway(self._url, job=job_name, registry=self._registry)
            print(f"Pushed metric {metric_name}={metric_value} to {self._url}")
        except Exception as e:
            print(f"Failed to push metric {metric_name} with value {metric_value}: {e}")
            raise
