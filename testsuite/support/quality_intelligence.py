# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/quality_intelligence.rb.

Provides QualityIntelligence: reports bootstrap, onboarding, and
synchronization durations to the Prometheus push gateway via MetricsCollector.
"""

import os

from support.metrics_collector import MetricsCollector

_QI = "quality_intelligence"


class QualityIntelligence:
    def __init__(self):
        url = os.getenv(
            "PROMETHEUS_PUSH_GATEWAY_URL", "http://nsa.mgr.suse.de:9091")
        self._collector = MetricsCollector(url)
        self._environment = os.getenv("SERVER", "unknown")

    def push_bootstrap_duration(self, system: str, duration: float):
        """
        Report the time to complete a bootstrap of the given system.

        :param system: the system name
        :param duration: the duration in seconds
        """
        self._collector.push_metrics(
            _QI,
            "system_bootstrap_duration_seconds",
            duration,
            {"system": system, "environment": self._environment})

    def push_onboarding_duration(self, system: str, duration: float):
        """
        Report the time to complete the onboarding of the given system.

        :param system: the system name
        :param duration: the duration in seconds
        """
        self._collector.push_metrics(
            _QI,
            "system_onboarding_duration_seconds",
            duration,
            {"system": system, "environment": self._environment})

    def push_synchronization_duration(self, product_name: str, duration: float):
        """
        Report the time to complete a synchronization of the given product.

        :param product_name: the product name
        :param duration: the duration in seconds
        """
        self._collector.push_metrics(
            _QI,
            "product_synch_duration_seconds",
            duration,
            {"system": product_name, "environment": self._environment})
