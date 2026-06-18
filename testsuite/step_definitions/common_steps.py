# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/common_steps.rb.

Covers general product functionality steps and those that do not fit into
any other category.
"""

import re
import time
from datetime import datetime

from pytest_bdd import given, when, then, parsers

from support.commonlib import (
    check_text,
    wait_for_ajax,
    rh_host,
    deb_host,
    repeat_until_timeout,
)
from support.remote_nodes_env import get_target, get_system_name
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Debugging / screenshots
# ---------------------------------------------------------------------------

@when(parsers.re(r'I save a screenshot as "(?P<filename>[^"]+)"'))
def step_save_screenshot(page, filename: str):
    page.screenshot(path=filename)


# ---------------------------------------------------------------------------
# Wait / sleep
# ---------------------------------------------------------------------------

@when(parsers.re(r'I wait for "(?P<seconds>\d+)" seconds?'))
def step_wait_for_seconds(seconds: str):
    time.sleep(int(seconds))


# ---------------------------------------------------------------------------
# System info checks (browser)
# ---------------------------------------------------------------------------

@then(parsers.re(r'the hostname for "(?P<host>[^"]*)" should be correct'))
def step_hostname_should_be_correct(page, host: str):
    node = get_target(host)
    assert check_text(page, node.hostname), f"Hostname {node.hostname} not found on page"


@then(parsers.re(r'the kernel for "(?P<host>[^"]*)" should be correct'))
def step_kernel_should_be_correct(page, host: str):
    node = get_target(host)
    kernel_version, _code = node.run("uname -r")
    kernel_version = kernel_version.strip()
    assert check_text(page, kernel_version), f"Kernel version {kernel_version} not found on page"


@then(parsers.re(r'the OS version for "(?P<host>[^"]*)" should be correct'))
def step_os_version_should_be_correct(page, host: str):
    node = get_target(host)
    os_version = node.os_version
    os_family = node.os_family
    if "sles" in os_family:
        display_version = os_version.replace("-SP", " SP")
        assert check_text(page, display_version), f"OS version {display_version} not found on page"


@then(parsers.re(r'the IPv4 address for "(?P<host>[^"]*)" should be correct'))
def step_ipv4_address_should_be_correct(page, host: str):
    node = get_target(host)
    ipv4_address = node.public_ip
    assert check_text(page, ipv4_address), f"IPv4 address {ipv4_address} not found on page"


@then(parsers.re(r'the IPv6 address for "(?P<host>[^"]*)" should be correct'))
def step_ipv6_address_should_be_correct(page, host: str):
    node = get_target(host)
    interface, code = node.run(f"ip -6 address show {node.public_interface}")
    assert code == 0, "Failed to get IPv6 address"
    ipv6_addresses = re.findall(r'(?:2[:0-9a-f]*|fe80:[:0-9a-f]*)', interface)
    ipv6_cell = page.locator("xpath=//td[text()='IPv6 Address:']/following-sibling::td[1]")
    ipv6_address = ipv6_cell.inner_text()
    assert ipv6_address in ipv6_addresses, \
        f"IPv6 address {ipv6_address} not in list {ipv6_addresses}"


@then(parsers.re(r'the system ID for "(?P<host>[^"]*)" should be correct'))
def step_system_id_should_be_correct(page, api_test, host: str):
    system_name = get_system_name(host)
    results = api_test.system.search_by_name(system_name)
    client_id = str(results[0]["id"])
    assert check_text(page, client_id), f"System ID {client_id} not found on page"


@then(parsers.re(r'the system name for "(?P<host>[^"]*)" should be correct'))
def step_system_name_should_be_correct(page, host: str):
    system_name = get_system_name(host)
    assert check_text(page, system_name), f"System name {system_name} not found on page"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@when(parsers.re(r'I wait until event "(?P<event>[^"]*)" is completed'))
def step_wait_until_event_completed(page, event: str):
    step_wait_at_most_until_event_completed(page, str(DEFAULT_TIMEOUT), event)


@when(parsers.re(
    r'I wait at most (?P<final_timeout>\d+) seconds until event "(?P<event>[^"]*)" is completed'
))
def step_wait_at_most_until_event_completed(page, final_timeout: str, event: str):
    _wait_for_event_ui(page, 180, int(final_timeout), event)


@when(parsers.re(
    r'I wait (?P<pickup_timeout>\d+) seconds until the event is picked up '
    r'and (?P<complete_timeout>\d+) seconds until the event "(?P<event>[^"]*)" is completed'
))
def step_wait_event_picked_up_and_completed(page, pickup_timeout: str, complete_timeout: str, event: str):
    _wait_for_event_ui(page, int(pickup_timeout), int(complete_timeout), event)


def _wait_for_event_ui(page, pickup_timeout: int, complete_timeout: int, event: str):
    """Navigate through the event pages and wait for the event to complete."""
    from support.embedded_steps.navigation_helper import follow_left_menu_link, wait_for_text
    # Navigate to Pending Events
    page.get_by_text("Events").first.click()
    wait_for_text(page, "Pending Events")
    page.get_by_text("Pending").click()
    wait_for_text(page, "Pending Events")

    # Wait for event to be picked up (disappear from Pending)
    def _disappeared():
        if not page.locator(f"text={event}").count():
            return True
        page.reload()
        return None

    repeat_until_timeout(_disappeared, timeout=pickup_timeout,
                         message=f"Event '{event}' was not picked up")

    # Navigate to History
    page.get_by_text("History").click()
    wait_for_text(page, "System History")

    def _appeared():
        if page.locator(f"text={event}").count():
            return True
        page.reload()
        return None

    repeat_until_timeout(_appeared, timeout=60, message=f"Event '{event}' not in history")

    # Click the event link
    page.get_by_text(event).first.click()
    wait_for_text(page, event)

    # Wait for completion
    def _completed():
        if page.locator("text=Completed").count():
            return True
        page.reload()
        return None

    repeat_until_timeout(_completed, timeout=complete_timeout,
                         message=f"Event '{event}' did not complete")


@when(parsers.re(
    r'I wait until I see the event "(?P<event>[^"]*)" completed during last minute, refreshing the page'
))
def step_wait_event_completed_last_minute(page, event: str):
    def _find_recent_event():
        now = datetime.now()
        current_minute = now.strftime('%H:%M')
        previous_minute = datetime.fromtimestamp(now.timestamp() - 60).strftime('%H:%M')
        xpath = (f"//a[contains(text(),'{event}')]/../..//td[4]/time"
                 f"[contains(text(),'{current_minute}') or contains(text(),'{previous_minute}')]"
                 f"/../../td[3]/a[1]")
        if page.locator(f"xpath={xpath}").count():
            return True
        page.reload()
        return None

    repeat_until_timeout(_find_recent_event, message=f"Couldn't find the event {event}")


@when(parsers.re(
    r'I wait up to (?P<waiting_time>\d+) minutes to see "(?P<text>[^"]*)" '
    r'in the last lines of "(?P<file>[^"]*)" on "(?P<host>[^"]*)"'
))
def step_wait_for_text_in_file_tail(waiting_time: str, text: str, file: str, host: str):
    node = get_target(host)
    timeout_seconds = int(waiting_time) * 60
    node.run_until_ok(f"tail -n 10 {file} | grep -E '{text}'", timeout=timeout_seconds)


@when(parsers.re(r'I follow the event "(?P<event>[^"]*)" completed during last minute'))
def step_follow_event_completed_last_minute(page, event: str):
    now = datetime.now()
    current_minute = now.strftime('%H:%M')
    previous_minute = datetime.fromtimestamp(now.timestamp() - 60).strftime('%H:%M')
    xpath = (f"//a[contains(text(), '{event}')]/../..//td[4]/time"
             f"[contains(text(),'{current_minute}') or contains(text(),'{previous_minute}')]"
             f"/../../td[3]/a[1]")
    page.locator(f"xpath={xpath}").click()


# ---------------------------------------------------------------------------
# Spacewalk errors
# ---------------------------------------------------------------------------

@then(parsers.re(r'the up2date logs on "(?P<host>[^"]*)" should contain no Traceback error'))
def step_up2date_logs_no_traceback(host: str):
    node = get_target(host)
    cmd = "if grep 'Traceback' /var/log/up2date ; then exit 1; else exit 0; fi"
    _out, code = node.run(cmd)
    assert code == 0, "Traceback error found, check the client up2date logs"


# ---------------------------------------------------------------------------
# Remote command multiline entry (browser step)
# ---------------------------------------------------------------------------

@when("I enter as remote command this script in")
def step_enter_remote_command_script(page, step):
    """Fill the remote command textarea with the docstring body."""
    body = step.text if hasattr(step, "text") else ""
    page.locator('xpath=//textarea[@name="script_body"]').fill(body)


# ---------------------------------------------------------------------------
# Bare metal / hardware checks
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check the ram value of the "(?P<host>[^"]*)"'))
def step_check_ram_value(page, host: str):
    node = get_target(host)
    get_ram_value = r"grep MemTotal /proc/meminfo | awk '{print $2}'"
    ram_value, _code = node.run(get_ram_value)
    ram_value = ram_value.strip()
    ram_mb = int(ram_value) // 1024
    assert check_text(page, str(ram_mb)), f"RAM value {ram_mb} not found on page"


@when(parsers.re(r'I check the MAC address value of the "(?P<host>[^"]*)"'))
def step_check_mac_address_value(page, host: str):
    node = get_target(host)
    mac_address, _code = node.run("cat /sys/class/net/eth0/address")
    mac_address = mac_address.strip().lower()
    assert check_text(page, mac_address), f"MAC address {mac_address} not found on page"


@then(parsers.re(r'I should see the CPU frequency of the "(?P<host>[^"]*)"'))
def step_see_cpu_frequency(page, host: str):
    node = get_target(host)
    cpu_freq, _code = node.run("cat /proc/cpuinfo | grep -i 'CPU MHz'")
    cpu_freq_clean = cpu_freq.replace(" ", "")
    cpu_parts = cpu_freq_clean.split(".")
    cpu_mhz = re.sub(r'[^\d]', '', cpu_parts[0])
    cpu_ghz = int(cpu_mhz) // 1000
    assert check_text(page, f"{cpu_ghz} GHz"), f"CPU frequency {cpu_ghz} GHz not found on page"


@then(parsers.re(r'I should see the power is "(?P<status>[^"]*)"'))
def step_see_power_status(page, status: str):
    container = page.locator("xpath=//*[@for='powerStatus']/..")

    def _check_power():
        if check_text(page, status):
            return True
        page.get_by_role("button", name="Get status").click()
        return None

    repeat_until_timeout(_check_power, message=f"power is not {status}")
    assert check_text(page, status), f"Power status {status} not found"


# ---------------------------------------------------------------------------
# Channel selection
# ---------------------------------------------------------------------------

@when(parsers.re(r'I select "(?P<label>.*?)" as the origin channel'))
def step_select_origin_channel(page, label: str):
    page.locator("#original_id").select_option(label=label)


# ---------------------------------------------------------------------------
# Systems page
# ---------------------------------------------------------------------------

@given("I am on the Systems page")
def step_am_on_systems_page(page):
    from support.embedded_steps.navigation_helper import follow_left_menu
    follow_left_menu(page, "Systems > System List > All")
    # Wait until loading is complete
    def _not_loading():
        if not page.locator("text=Loading...").count():
            return True
        return None
    repeat_until_timeout(_not_loading, timeout=30, message="Page still loading")


# ---------------------------------------------------------------------------
# File attachment
# ---------------------------------------------------------------------------

@when(parsers.re(r'I attach the file "(?P<path>.*)" to "(?P<field>.*)"'))
def step_attach_file(page, path: str, field: str):
    import os
    upload_dir = os.path.join(os.path.dirname(__file__), "../features/upload_files")
    canonical_path = os.path.realpath(os.path.join(upload_dir, path))
    page.locator(f"[name='{field}'], #{field}").first.set_input_files(canonical_path)


# ---------------------------------------------------------------------------
# Metadata refresh
# ---------------------------------------------------------------------------

@when(parsers.re(r'I refresh the metadata for "(?P<host>[^"]*)"'))
def step_refresh_metadata(host: str):
    node = get_target(host)
    os_family = node.os_family
    if any(os_family.startswith(p) for p in ("opensuse", "sles", "suse", "micro")):
        node.run("zypper --non-interactive refresh -s", retries=5)
    elif any(os_family.startswith(p) for p in ("centos", "rocky")):
        node.run("yum clean all && yum makecache", timeout=600)
    elif os_family.startswith("ubuntu"):
        node.run("apt-get update")
    else:
        raise NotImplementedError(
            f"The host {host} (os_family={os_family!r}) has no metadata refresh implementation"
        )


# ---------------------------------------------------------------------------
# Patch metadata
# ---------------------------------------------------------------------------

@then(parsers.re(r"I should have '(?P<text>[^']*)' in the patch metadata for \"(?P<host>[^\"]*)\""  ))
def step_should_have_in_patch_metadata(text: str, host: str):
    node = get_target(host)
    arch, _code = node.run("uname -m")
    arch = arch.strip()
    cmd = f"zgrep '{text}' /var/cache/zypp/raw/susemanager:fake-rpm-suse-channel/repodata/*updateinfo.xml.gz"
    node.run(cmd, timeout=500)


# ---------------------------------------------------------------------------
# Package steps
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see package "(?P<package>[^"]*)"'))
def step_should_see_package(page, package: str):
    assert check_text(page, package), f"Package {package} not found on page"


@given(parsers.re(r'metadata generation finished for "(?P<channel>[^"]*)"'))
def step_metadata_generation_finished(channel: str):
    get_target("server").run_until_ok(
        f"ls /var/cache/rhn/repodata/{channel}/*updateinfo.xml.gz"
    )


@when(parsers.re(
    r'I push package "(?P<package_filepath>[^"]*)" into "(?P<channel>[^"]*)" '
    r'channel through "(?P<minion>[^"]*)"'
))
def step_push_package_into_channel(package_filepath: str, channel: str, minion: str):
    server = get_target("server")
    command = (
        f"mgrpush -u admin -p admin --server={server.full_hostname} "
        f"--nosig -c {channel} {package_filepath}"
    )
    get_target(minion).run(command, timeout=500)
    import os
    package_filename = os.path.basename(package_filepath)
    server.run_until_ok(
        f'find /var/spacewalk/packages -name "{package_filename}" | grep -q "{package_filename}"',
        timeout=500
    )


# ---------------------------------------------------------------------------
# ReportDB task schedule
# ---------------------------------------------------------------------------

@when("I schedule a task to update ReportDB")
def step_schedule_task_to_update_reportdb(page):
    from support.embedded_steps.navigation_helper import follow_left_menu
    follow_left_menu(page, "Admin > Task Schedules")
    page.get_by_text("update-reporting-default").click()
    page.get_by_text("mgr-update-reporting-bunch").click()
    page.get_by_role("button", name="Single Run Schedule").click()
    assert check_text(page, "bunch was scheduled"), "Expected 'bunch was scheduled' text"


# ---------------------------------------------------------------------------
# User creation result checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'the user creation should fail with error containing "(?P<expected_text>[^"]*)"'))
def step_user_creation_should_fail(expected_text: str, context_store):
    status = context_store.get("user_creation_status")
    error_message = context_store.get("user_creation_error", "")
    assert status == "error", f"Expected user creation to fail, but status was '{status}'"
    assert expected_text in error_message, \
        f"Expected error message to include '{expected_text}', but got '{error_message}'"


@then("the user creation should succeed")
def step_user_creation_should_succeed(context_store):
    status = context_store.get("user_creation_status")
    assert status == "success", f"Expected user creation to succeed, but status was '{status}'"
