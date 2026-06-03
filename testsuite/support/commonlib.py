# Copyright (c) 2013-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/commonlib.rb.

Provides core utilities used across the testsuite:
  - repeat_until_timeout  — polling loop with timeout / retry cap
  - product detection     — Uyuni vs SUSE Manager
  - browser helpers       — Playwright wrappers (check_text, wait_for_ajax, …)
  - network helpers       — get_reverse_net
  - host classification   — suse_host, rh_host, deb_host, transactional_system
  - misc utilities        — get_client_type, get_future_time, escape_regex, …
"""

import re
import time
from datetime import datetime, timedelta

from support.env import DEFAULT_TIMEOUT, CODE_COVERAGE_MODE, CAPYBARA_TIMEOUT


# ---------------------------------------------------------------------------
# Core: repeat_until_timeout
# ---------------------------------------------------------------------------

def repeat_until_timeout(fn, *, timeout=DEFAULT_TIMEOUT, retries=None,
                         message=None, report_result=False, dont_raise=False):
    """
    Call fn() repeatedly until it returns truthy or timeout elapses.

    fn() must return None/False to continue, any truthy value to stop.
    Optional *retries* parameter caps the number of attempts.
    When *dont_raise* is True, returns None instead of raising on timeout/retry
    exhaustion.
    """
    effective_timeout = timeout * 2 if CODE_COVERAGE_MODE else timeout
    start = time.time()
    attempts = 0
    last_result = None
    try:
        while (time.time() - start) < effective_timeout:
            if retries is not None and attempts >= retries:
                break
            last_result = fn()
            attempts += 1
            if last_result:
                return last_result

        detail = _format_detail(message, last_result, report_result)
        if retries is not None and attempts >= retries:
            raise RuntimeError(f"Giving up after {attempts} attempts{detail}")
        raise TimeoutError(f"Timeout after {effective_timeout}s{detail}")
    except (TimeoutError, RuntimeError) as e:
        if dont_raise:
            return None
        raise


def _format_detail(message, last_result, report_result):
    """Build the detail suffix for timeout/retry error messages."""
    detail = ""
    if message:
        detail += f": {message}"
    if report_result and last_result is not None:
        detail += f", last result was: {last_result}"
    return detail


# ---------------------------------------------------------------------------
# Product detection
# ---------------------------------------------------------------------------

_product_cache = {}


def product():
    """Detect product: 'Uyuni' or 'SUSE Manager'."""
    if "name" in _product_cache:
        return _product_cache["name"]
    from support.remote_nodes_env import get_target
    server = get_target("server")
    patterns = {
        "patterns-uyuni_server": "Uyuni",
        "patterns-suma_server": "SUSE Manager",
    }
    for pattern, name in patterns.items():
        _out, code = server.run(f"rpm -q {pattern}", check_errors=False)
        if code == 0:
            _product_cache["name"] = name
            return name
    raise NotImplementedError("Could not determine product")


def product_version_full():
    """Return the full product version string from salt grains, or None."""
    from support.remote_nodes_env import get_target
    server = get_target("server")
    out, code = server.run(
        "venv-salt-call --local grains.get product_version | tail -n 1",
        runs_in_container=False)
    if code == 0 and out.strip():
        return out.strip()
    return None


def transactional_system(host, *, runs_in_container=True):
    """Return True if the host runs a transactional update system."""
    from support.remote_nodes_env import get_target
    node = get_target(host)
    _out, code = node.run(
        "which transactional-update",
        runs_in_container=runs_in_container, check_errors=False)
    return code == 0


# ---------------------------------------------------------------------------
# Host OS-family helpers
# ---------------------------------------------------------------------------

_SUSE_OS_FAMILIES = frozenset([
    "sles", "opensuse", "opensuse-tumbleweed", "opensuse-leap",
    "sle-micro", "suse-microos", "opensuse-leap-micro",
])

_RH_OS_FAMILIES = frozenset([
    "alma", "almalinux", "amzn", "centos", "liberty", "ol",
    "oracle", "rocky", "redhat", "rhel",
])

_DEB_OS_FAMILIES = frozenset(["debian", "ubuntu"])


def suse_host(name, *, runs_in_container=True):
    """Return True if the named host is a SUSE-family system."""
    from support.remote_nodes_env import get_target
    node = get_target(name)
    os_family = node.os_family if runs_in_container else node.local_os_family
    return os_family in _SUSE_OS_FAMILIES


def slemicro_host(name, *, runs_in_container=True):
    """Return True if the host is a SLE/SL Micro system."""
    from support.remote_nodes_env import get_target
    node = get_target(name)
    os_family = node.os_family if runs_in_container else node.local_os_family
    return ("sle-micro" in os_family or
            "suse-microos" in os_family or
            "sl-micro" in os_family)


def leapmicro_host(name, *, runs_in_container=True):
    """Return True if the host is an openSUSE Leap Micro system."""
    from support.remote_nodes_env import get_target
    node = get_target(name)
    os_family = node.os_family if runs_in_container else node.local_os_family
    return "opensuse-leap-micro" in os_family


def rh_host(name):
    """Return True if the host is a Red Hat-like system."""
    from support.remote_nodes_env import get_target
    os_family = get_target(name).os_family
    return os_family in _RH_OS_FAMILIES


def deb_host(name):
    """Return True if the host is a Debian-based system."""
    from support.remote_nodes_env import get_target
    os_family = get_target(name).os_family
    return os_family in _DEB_OS_FAMILIES


# ---------------------------------------------------------------------------
# Client type
# ---------------------------------------------------------------------------

def get_client_type(name):
    """Return 'traditional' for *_client hosts, 'salt' otherwise."""
    return "traditional" if "_client" in name else "salt"


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def get_reverse_net(net):
    """
    Return the reverse DNS in-addr.arpa representation of a /24 network.

    Example: '192.168.1.0'  →  '1.168.192.in-addr.arpa'

    Note: works correctly for /24 masks only (matches the Ruby original).
    """
    parts = net.split(".")
    return f"{parts[2]}.{parts[1]}.{parts[0]}.in-addr.arpa"


def net_prefix(private_net):
    """Return the network prefix (e.g. '192.168.1.') from a CIDR string."""
    return re.sub(r"\.0+/24$", ".", private_net)


# ---------------------------------------------------------------------------
# Browser helpers (Playwright)
# ---------------------------------------------------------------------------

def check_text(page, text1, *, text2=None, timeout=None):
    """
    Check if *text1* (or optionally *text2*) is visible on the page.

    Resilient to page navigation errors: any exception returns False.
    Uses short per-call timeouts so that an outer repeat_until_timeout can
    fire reliably (avoids a race between two concurrent timeouts).
    """
    if timeout is None:
        timeout = CAPYBARA_TIMEOUT
    try:
        loc = page.get_by_text(text1).first
        if loc.is_visible(timeout=timeout * 1000):
            return True
        if text2:
            loc2 = page.get_by_text(text2).first
            if loc2.is_visible(timeout=timeout * 1000):
                return True
        return False
    except Exception:
        return False


def wait_for_ajax(page, timeout_ms=30000):
    """Wait for the .senna-loading spinner to disappear."""
    try:
        page.locator(".senna-loading").wait_for(
            state="hidden", timeout=timeout_ms)
    except Exception:
        pass


def click_button_and_wait(page, text, **kwargs):
    """Click a button by visible text and wait for any AJAX transition."""
    page.get_by_role("button", name=text).click(**kwargs)
    wait_for_ajax(page)


def click_link_and_wait(page, text, **kwargs):
    """Click a link by visible text and wait for any AJAX transition."""
    page.get_by_role("link", name=text).click(**kwargs)
    wait_for_ajax(page)


def click_link_or_button_and_wait(page, text, **kwargs):
    """Click a link or button by text and wait for any AJAX transition."""
    # Try link first, fall back to button
    try:
        page.get_by_role("link", name=text).click(**kwargs)
    except Exception:
        page.get_by_role("button", name=text).click(**kwargs)
    wait_for_ajax(page)


def refresh_page(page):
    """Reload the page, auto-dismissing any confirmation dialog."""
    page.on("dialog", lambda d: d.accept())
    try:
        page.evaluate("window.location.reload()")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass


def count_table_items(page):
    """
    Parse and return the item count from the UI table count button.

    Returns the text after 'of ' in the button label (e.g. '42').
    """
    btn = page.locator('xpath=//button[contains(text(), "Items ")]')
    text = btn.text_content()
    return text.split("of ")[1].strip()


def current_url(page):
    """Return the current URL of the browser page."""
    return page.url


# ---------------------------------------------------------------------------
# Misc utilities
# ---------------------------------------------------------------------------

def escape_regex(text):
    """
    Escape special regex characters so that *text* matches literally.

    Ported from the Ruby original — escapes: $ . * [ / ^
    """
    return re.sub(r'([$.*\[/^])', r'\\\1', text)


def get_future_time(minutes_to_add):
    """
    Return a future time string in 'HH:MM' format.

    :param minutes_to_add: int — number of minutes to add to the current time.
    :raises TypeError: if minutes_to_add is not an int.
    """
    if not isinstance(minutes_to_add, int):
        raise TypeError("minutes_to_add should be an int")
    future = datetime.now() + timedelta(minutes=minutes_to_add)
    return future.strftime("%H:%M")


def reportdb_server_query(query):
    """
    Return a shell command string that runs *query* against the report DB.

    The caller is responsible for executing the returned string on the server.
    """
    return f'echo "{query}" | spacewalk-sql --reportdb --select-mode -'


def generate_repository_name(repo_url):
    """
    Generate a short repository name from a full repository URL.

    Strips known URL prefixes and replaces / and : with _, truncated to 64 chars.
    """
    name = repo_url.strip()
    host_pattern = (
        r"(?:download\.suse\.de|download\.opensuse\.org"
        r"|minima-mirror-ci-bv\.mgr[^/]*"
        r"|[^/]*\.compute\.internal)"
    )
    prefixes = [
        rf"http://{host_pattern}/ibs/SUSE:/Maintenance:/",
        rf"http://{host_pattern}/download/ibs/SUSE:/Maintenance:/",
        rf"http://{host_pattern}/download/ibs/SUSE:/",
        rf"http://{host_pattern}/repositories/systemsmanagement:/",
        rf"http://{host_pattern}/SUSE:/",
        rf"http://{host_pattern}/ibs/Devel:/Galaxy:/Manager:/",
        rf"http://{host_pattern}/SUSE:/Maintenance:/",
        rf"http://{host_pattern}/ibs/SUSE:/SLE-15:/Update:/Products:/MultiLinuxManagerTools/images/repo/",
        rf"http://{host_pattern}/ibs/SUSE:/",
    ]
    for prefix in prefixes:
        name = re.sub(prefix, "", name, count=1)
    name = name.replace("/", "_").replace(":", "_")
    return name[:64]


def filter_channels(channels, filters=None):
    """
    Return a copy of *channels* with any entry containing a filter string removed.

    :param channels: list of channel name strings
    :param filters:  list of filter substrings (default: empty list)
    """
    if not channels:
        print("Warning: No channels to filter")
        return []
    if filters is None:
        filters = []
    result = list(channels)
    for f in filters:
        result = [c for c in result if f not in c]
    return result
