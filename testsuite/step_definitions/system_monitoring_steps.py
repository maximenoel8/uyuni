# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/system_monitoring_steps.rb.

Covers steps for reporting bootstrap, onboarding and synchronization
durations as part of quality intelligence data collection.
"""

from pytest_bdd import given, when, then, parsers

from support.system_monitoring import last_bootstrap_duration, last_onboarding_duration
from support.remote_nodes_env import get_target


@when(parsers.re(r'I report the bootstrap duration for "(?P<host>[^"]*)"'))
def step_monitoring_report_bootstrap_duration(host: str, quality_intelligence):
    from support.env import QUALITY_INTELLIGENCE_MODE
    if not QUALITY_INTELLIGENCE_MODE:
        return
    duration = last_bootstrap_duration(host)
    if quality_intelligence:
        quality_intelligence.push_bootstrap_duration(host, duration)


@when(parsers.re(r'I report the onboarding duration for "(?P<host>[^"]*)"'))
def step_monitoring_report_onboarding_duration(host: str, quality_intelligence):
    from support.env import QUALITY_INTELLIGENCE_MODE
    if not QUALITY_INTELLIGENCE_MODE:
        return
    duration = last_onboarding_duration(host)
    if quality_intelligence:
        quality_intelligence.push_onboarding_duration(host, duration)


@when(parsers.re(r'I report the synchronization duration for "(?P<product>[^"]*)"'))
def step_report_synchronization_duration(product: str, quality_intelligence):
    from support.env import QUALITY_INTELLIGENCE_MODE
    if not QUALITY_INTELLIGENCE_MODE:
        return
    from support.system_monitoring import product_synchronization_duration
    duration = product_synchronization_duration(product)
    if quality_intelligence:
        quality_intelligence.push_synchronization_duration(product, duration)
