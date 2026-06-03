# Copyright (c) 2024-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/remote_nodes_env.rb.

Provides environment validation and the get_target() helper used across
the testsuite to lazily initialise RemoteNode instances.
"""

import os
import warnings
from pathlib import Path

from support.constants import ENV_VAR_BY_HOST
from support.remote_node import RemoteNode, node_by_host, named_nodes


def _validate_environment():
    """
    Validate that the minimum required environment variables are set.

    Raises EnvironmentError if SERVER is not defined.
    Emits warnings for optional hosts that are absent when a BV
    custom_repositories.json is not present.
    """
    if not os.getenv("SERVER"):
        raise EnvironmentError("Server IP address or domain name variable empty")

    custom_repos_path = (
        Path(__file__).parent.parent
        / "features" / "upload_files" / "custom_repositories.json"
    )
    if not custom_repos_path.exists():
        for var, label in [
            ("PROXY", "Proxy"),
            ("MINION", "Minion"),
            ("BUILD_HOST", "Buildhost"),
            ("RHLIKE_MINION", "Red Hat-like minion"),
            ("DEBLIKE_MINION", "Debian-like minion"),
            ("SSH_MINION", "SSH minion"),
            ("PXEBOOT_MAC", "PXE boot MAC address"),
        ]:
            if not os.getenv(var):
                warnings.warn(f"{label} IP address or domain name variable empty")


def get_target(host: str, *, refresh: bool = False) -> "RemoteNode":
    """
    Get or lazily create a RemoteNode for the given host.

    The node is cached in node_by_host after first creation.
    Pass refresh=True to force re-initialisation (e.g. after a reboot).
    """
    node = node_by_host.get(host)
    if node is None or refresh:
        node = RemoteNode(host)
    return node
