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


# ---------------------------------------------------------------------------
# Uptime check
# ---------------------------------------------------------------------------

@then(parsers.re(r'the uptime for "(?P<host>[^"]*)" should be correct'))
def step_uptime_should_be_correct(page, host: str):
    node = get_target(host)
    raw, _ = node.run("cat /proc/uptime")
    seconds = float(raw.split()[0])
    minutes = seconds / 60.0
    hours = minutes / 60.0
    days = hours / 24.0

    rounded_minutes = round(minutes)
    rounded_hours = round(hours)
    eleven_hours = 39_600
    rounded_days = round((seconds + eleven_hours) / 86_400.0)

    valid = []
    if (days >= 1 and rounded_days < 2) or (days < 1 and rounded_hours >= 22):
        valid = ["a day ago"]
    elif 1 < rounded_hours <= 21:
        valid = [f"{rounded_hours + d} hours ago" for d in (-1, 0, 1)]
        valid = ["an hour ago" if t == "1 hours ago" else t for t in valid]
    elif rounded_minutes >= 45 and rounded_hours == 1:
        valid = ["an hour ago"]
    elif 1 < rounded_minutes and rounded_hours <= 1:
        valid = [f"{rounded_minutes + d} minutes ago" for d in (-1, 0, 1)]
        valid = ["a minute ago" if t == "1 minutes ago" else t for t in valid]
    elif seconds >= 45 and rounded_minutes == 1:
        valid = ["a minute ago"]
    elif seconds < 45:
        valid = ["a few seconds ago"]
    elif rounded_days < 25:
        valid = [f"{rounded_days + d} days ago" for d in (-1, 0, 1)]
        valid = ["a day ago" if t == "1 days ago" else t for t in valid]
    else:
        valid = ["a month ago"]

    ui_text = page.locator(
        "xpath=//td[contains(text(), 'Last Booted')]/following-sibling::td/time"
    ).text_content()
    assert ui_text, f"Uptime text for host '{host}' not found"
    assert ui_text in valid, (
        f"Uptime for '{host}': expected one of {valid}, got '{ui_text}'"
    )
