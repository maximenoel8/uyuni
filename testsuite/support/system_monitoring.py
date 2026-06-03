# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/system_monitoring.rb.

Provides helpers that measure durations of key CI lifecycle events:
  - last_bootstrap_duration
  - last_onboarding_duration
  - product_synchronization_duration
  - channel_synchronization_duration

All functions raise RuntimeError (equivalent to Ruby's ScriptError) when
the expected data cannot be found in the logs or API.
"""

import os
import re

from support.remote_nodes_env import get_target
from support.api_test import new_api_client
from support.commonlib import filter_channels
from support.constants import CHANNEL_TO_SYNC_BY_OS_PRODUCT_VERSION
from support.env import BETA_ENABLED

_REPOSYNC_LOG_REMOTE = "/var/log/rhn/reposync.log"
_REPOSYNC_LOG_LOCAL = "/tmp/reposync.log"


def last_bootstrap_duration(host: str) -> float:
    """
    Return the last bootstrap duration for the given host in seconds.

    Reads the last 100 lines of rhn_web_api.log on the server and extracts
    the TIME value from the line matching the host name and 'systems.bootstrap'.

    :param host: logical host name (e.g. 'minion', 'ssh_minion')
    :return: duration in seconds as a float
    :raises RuntimeError: if the bootstrap entry is not found in the logs
    """
    node = get_target(host)
    system_name = node.full_hostname
    server = get_target("server")
    lines, _code = server.run(
        "tail -n100 /var/log/rhn/rhn_web_api.log",
        check_errors=False,
    )
    duration = None
    for line in lines.splitlines():
        if system_name in line and "systems.bootstrap" in line:
            match = re.search(r"TIME: (\d+\.\d+) seconds", line)
            if match:
                duration = float(match.group(1))
    if duration is None:
        raise RuntimeError(f"Bootstrap duration not found for {host}")
    return duration


def last_onboarding_duration(host: str) -> float:
    """
    Return the last onboarding duration for the given host in seconds.

    Uses the XML-RPC / HTTP API to fetch the event history for the system
    and extracts the elapsed time of the last event that matches the
    onboarding summary pattern ('certs, channels, packages').

    :param host: logical host name
    :return: duration in seconds (completed − picked_up)
    :raises RuntimeError: if the onboarding event cannot be found or parsed
    """
    try:
        node = get_target(host)
        api = new_api_client()

        # Resolve system ID via the API
        systems = api.call("system.search.hostname", node.full_hostname)
        if not systems:
            raise RuntimeError(
                f"No system found with hostname {node.full_hostname}")
        system_id = systems[0]["id"]

        events = api.call("system.getEventHistory", system_id, 0, 10)
        onboarding_events = [
            e for e in events
            if "certs, channels, packages" in str(e.get("summary", ""))
        ]
        if not onboarding_events:
            raise RuntimeError(
                f"No onboarding event found for {host}")

        last_event_id = onboarding_events[-1]["id"]
        event_details = api.call(
            "system.getEventDetails", system_id, last_event_id)

        completed = _parse_event_time(event_details["completed"])
        picked_up = _parse_event_time(event_details["picked_up"])
        return (completed - picked_up).total_seconds()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Error extracting onboarding duration for {host}: {e}") from e


def product_synchronization_duration(os_product_version: str) -> int:
    """
    Return the total synchronization duration in seconds for the given
    OS product version, summed across all its configured channels.

    Reads /var/log/rhn/reposync.log from the server.

    :param os_product_version: e.g. 'SLES15-SP6'
    :return: total duration in seconds
    :raises RuntimeError: if channels for the product are not configured,
                          or if the reposync log is absent / empty
    """
    # Determine the current product key from the environment
    product = os.getenv("PRODUCT", "")
    channels_to_evaluate = (
        CHANNEL_TO_SYNC_BY_OS_PRODUCT_VERSION
        .get(product, {})
        .get(os_product_version)
    )
    if channels_to_evaluate is None:
        raise RuntimeError(
            f"Synchronization error: channels for {os_product_version} "
            f"in {product} not found")
    channels_to_evaluate = list(channels_to_evaluate)  # clone

    if channels_to_evaluate:
        print(
            f"Product: {product}\n"
            f"{CHANNEL_TO_SYNC_BY_OS_PRODUCT_VERSION}\n"
            f"{channels_to_evaluate}")
    if not BETA_ENABLED:
        channels_to_evaluate = filter_channels(channels_to_evaluate, ["beta"])
    print(f"Channels to evaluate:\n{channels_to_evaluate}")

    server = get_target("server")
    server.extract(_REPOSYNC_LOG_REMOTE, _REPOSYNC_LOG_LOCAL)
    if not os.path.exists(_REPOSYNC_LOG_LOCAL) or \
            os.path.getsize(_REPOSYNC_LOG_LOCAL) == 0:
        raise RuntimeError(
            "The file with repository synchronization logs doesn't exist or is empty")

    duration = 0
    channel_to_evaluate = False
    matches = 0
    channel_name = ""
    log_content = []
    with open(_REPOSYNC_LOG_LOCAL) as fh:
        log_content = fh.readlines()

    for line in log_content:
        if "Channel: " in line:
            channel_name = line.split("Channel: ")[1].strip()
            channel_to_evaluate = channel_name in channels_to_evaluate
        if "Total time: " in line and channel_to_evaluate:
            match = re.search(r"Total time: (\d+):(\d+):(\d+)", line)
            if match:
                hours, minutes, seconds = (int(x) for x in match.groups())
                total_seconds = hours * 3600 + minutes * 60 + seconds
                print(
                    f"Channel {channel_name} synchronization duration: "
                    f"{total_seconds} seconds")
                duration += total_seconds
                matches += 1
                channel_to_evaluate = False

    if matches < len(channels_to_evaluate):
        print(
            f"Error extracting the synchronization duration of {os_product_version}")
        print(f"Content of reposync.log:\n{''.join(log_content)}")

    return duration


def channel_synchronization_duration(channel: str) -> int:
    """
    Return the synchronization duration in seconds for a single channel.

    If the channel appears multiple times in reposync.log, returns the
    duration from the last occurrence.

    :param channel: channel name to look up
    :return: duration in seconds
    :raises RuntimeError: if the channel is not found in the reposync log
    """
    server = get_target("server")
    server.extract(_REPOSYNC_LOG_REMOTE, _REPOSYNC_LOG_LOCAL)
    if not os.path.exists(_REPOSYNC_LOG_LOCAL) or \
            os.path.getsize(_REPOSYNC_LOG_LOCAL) == 0:
        raise RuntimeError(
            "The file with repository synchronization logs doesn't exist or is empty")

    channel_found = False
    duration = 0
    matches = 0
    with open(_REPOSYNC_LOG_LOCAL) as fh:
        for line in fh:
            if "Channel: " in line:
                channel_name = line.split("Channel: ")[1].strip()
                if channel_name == channel:
                    channel_found = True
                    duration = 0
                    matches += 1
            if "Total time: " in line and channel_found:
                match = re.search(r"Total time: (\d+):(\d+):(\d+)", line)
                if match:
                    hours, minutes, seconds = (int(x) for x in match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds
                    channel_found = False

    if matches > 1:
        print(
            f"Channel {channel} was found {matches} times in the logs, "
            "we return the last synchronization time.")
    if matches == 0:
        raise RuntimeError(
            f"Error extracting the synchronization duration of {channel}")

    return duration


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_event_time(value):
    """Convert an event timestamp (xmlrpc.DateTime or ISO string) to datetime."""
    from datetime import datetime, timezone
    import xmlrpc.client
    if isinstance(value, xmlrpc.client.DateTime):
        return value.timetuple()  # returns time.struct_time; convert below
    # For xmlrpc.DateTime we need an actual datetime for subtraction
    if hasattr(value, "timetuple"):
        import calendar
        ts = calendar.timegm(value.timetuple())
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    # ISO string
    return datetime.fromisoformat(str(value))
