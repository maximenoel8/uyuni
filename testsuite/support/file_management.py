# Copyright (c) 2023-2025 SUSE LLC
# Licensed under the terms of the MIT license.

"""File management helpers ported from file_management.rb."""

import os
import re
import tempfile
import urllib.parse
import urllib.request
from http.client import HTTPConnection, HTTPSConnection

from support.remote_nodes_env import get_target


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_node(node_or_host):
    """Return a RemoteNode for *node_or_host*.

    If *node_or_host* is a string it is resolved via :func:`get_target`;
    otherwise it is returned as-is (assumed to already be a RemoteNode).
    """
    if isinstance(node_or_host, str):
        return get_target(node_or_host)
    return node_or_host


# ---------------------------------------------------------------------------
# File / folder predicates and operations
# ---------------------------------------------------------------------------

def file_exists(node_or_host, path: str) -> bool:
    """Check if a file exists on a node.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        path: Absolute path of the file to check.

    Returns:
        True if the file exists, False otherwise.
    """
    return _resolve_node(node_or_host).file_exists(path)


def file_delete(node_or_host, path: str):
    """Delete a file on a node.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        path: Absolute path of the file to delete.
    """
    _resolve_node(node_or_host).file_delete(path)


def folder_exists(node_or_host, path: str) -> bool:
    """Check if a folder exists on a node.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        path: Absolute path of the folder to check.

    Returns:
        True if the folder exists, False otherwise.
    """
    return _resolve_node(node_or_host).folder_exists(path)


def folder_delete(node_or_host, path: str):
    """Delete a folder on a node.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        path: Absolute path of the folder to delete.
    """
    _resolve_node(node_or_host).folder_delete(path)


# ---------------------------------------------------------------------------
# File transfer helpers
# ---------------------------------------------------------------------------

def file_extract(node_or_host, remote_file: str, local_file: str):
    """Extract (download) a remote file to a local path.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        remote_file: Path of the file on the remote node.
        local_file: Local destination path.
    """
    _resolve_node(node_or_host).extract(remote_file, local_file)


def file_inject(node_or_host, local_file: str, remote_file: str):
    """Inject (upload) a local file to a remote node.

    Args:
        node_or_host: A RemoteNode instance or host-name string.
        local_file: Path of the local source file.
        remote_file: Destination path on the remote node.
    """
    _resolve_node(node_or_host).inject(local_file, remote_file)


# ---------------------------------------------------------------------------
# Temporary file helpers
# ---------------------------------------------------------------------------

def generate_temp_file(name: str, content: str) -> str:
    """Generate a temporary file with the given name prefix and content.

    The caller is responsible for deleting the file when done.

    Args:
        name: Prefix for the temporary file name.
        content: Text content to write into the file.

    Returns:
        The absolute path of the created temporary file.
    """
    tmp = tempfile.NamedTemporaryFile(
        prefix=name, suffix=".tmp", delete=False, mode="w"
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Salt pillar helpers
# ---------------------------------------------------------------------------

def inject_salt_pillar_file(source: str, filename: str):
    """Create a Salt pillar file in the default pillar_roots location.

    Injects *source* to ``/srv/pillar/<filename>`` on the server node and
    sets ownership to ``salt:salt`` so Salt can read it.

    Args:
        source: Local path of the source file.
        filename: Destination filename (basename only) under ``/srv/pillar/``.

    Raises:
        ScriptError: If the file injection fails.
    """
    server = get_target("server")
    remote_path = f"/srv/pillar/{filename}"
    success = server.inject(source, remote_path)
    if not success:
        raise RuntimeError("File injection failed")
    server.run(f"chown -R salt:salt {remote_path}")


# ---------------------------------------------------------------------------
# Configuration file helpers
# ---------------------------------------------------------------------------

def get_variable_from_conf_file(host: str, file_path: str,
                                variable_name: str) -> str:
    """Read the value of a variable from a configuration file on a remote host.

    Matches lines of the form ``variable_name = value`` using ``sed``.

    Args:
        host: Host name (resolved via :func:`get_target`).
        file_path: Absolute path to the configuration file on the host.
        variable_name: Name of the variable to retrieve.

    Returns:
        The stripped value of the variable.

    Raises:
        RuntimeError: If the remote command exits with a non-zero return code.
    """
    node = get_target(host)
    out, return_code = node.run(
        f"sed -n 's/^{variable_name} = \\(.*\\)/\\1/p' < {file_path}"
    )
    if return_code != 0:
        raise RuntimeError(
            f"Reading {variable_name} from file on {host} {file_path} failed"
        )
    return out.strip()


# ---------------------------------------------------------------------------
# Checksum / repository helpers
# ---------------------------------------------------------------------------

_CHECKSUM_FILE_NAMES = [
    "CHECKSUM",
    "SHA256SUMS",
    "sha256sum.txt",
    # The file-specific names are generated dynamically in get_checksum_path.
]


def get_checksum_path(directory: str, original_file_name: str,
                      file_url: str) -> str:
    """Retrieve the SHA256 checksum file path for a downloaded file.

    When a mirror is configured (``$mirror`` global is truthy) the checksum
    file is expected to already be present in *directory*.  Otherwise the
    function attempts to download it from the same base URL.

    Args:
        directory: Remote directory where the original file resides.
        original_file_name: Basename of the file whose checksum is needed.
        file_url: Full URL from which the file was downloaded.

    Returns:
        The remote path to the checksum file.

    Raises:
        RuntimeError: If no checksum file can be found or downloaded.
    """
    import support.env as _env  # imported lazily to avoid circular imports

    checksum_names = [
        "CHECKSUM",
        "SHA256SUMS",
        "sha256sum.txt",
        f"{original_file_name}.CHECKSUM",
        f"{original_file_name}.sha256",
    ]

    server = get_target("server")

    if getattr(_env, "mirror", None):
        # Mirror path: checksum file should already be present alongside the file.
        output, _code = server.run(f"ls -1 {directory}",
                                   runs_in_container=False)
        files = output.splitlines()
        checksum_file = next(
            (f for f in files if f in checksum_names), None
        )
        if not checksum_file:
            raise RuntimeError(
                f"SHA256 checksum file not found in {directory}"
            )
        return f"{directory}/{checksum_file}"

    # Non-mirror path: attempt to download from the same base URL.
    base_url = file_url[: -len(original_file_name)]
    parsed = urllib.parse.urlparse(base_url)
    use_ssl = parsed.scheme == "https"
    host_name = parsed.hostname
    port = parsed.port or (443 if use_ssl else 80)
    base_path = parsed.path

    if use_ssl:
        conn = HTTPSConnection(host_name, port, timeout=10)
    else:
        conn = HTTPConnection(host_name, port, timeout=10)

    try:
        for name in checksum_names:
            checksum_path = base_path + name
            conn.request("HEAD", checksum_path)
            response = conn.getresponse()
            response.read()  # consume body
            if response.status == 200:
                checksum_url = base_url + name
                _output, code = server.run(
                    f"cd {directory} && curl --insecure {checksum_url} -o {name}",
                    runs_in_container=False,
                    timeout=10,
                )
                if code == 0:
                    return f"{directory}/{name}"
    finally:
        conn.close()

    raise RuntimeError(
        f"No SHA256 checksum file to download found for file at {file_url}"
    )


def checksum_with_file_valid(original_file_name: str, file_path: str,
                             checksum_path: str) -> bool:
    """Compute and verify the SHA256 checksum of a remote file against a checksum file.

    Args:
        original_file_name: Basename of the file to validate.
        file_path: Remote path to the file.
        checksum_path: Remote path to the checksum file.

    Returns:
        True if the checksum matches, False otherwise.

    Raises:
        RuntimeError: If the checksum entry cannot be found or parsed.
    """
    server = get_target("server")
    cmd = f"grep -v '^#' {checksum_path} | grep '{original_file_name}'"
    checksum_line, _code = server.run(cmd, runs_in_container=False)
    if not checksum_line:
        raise RuntimeError(
            f"SHA256 checksum entry for {original_file_name} not found in {checksum_path}"
        )

    match = re.search(r"\b([0-9a-fA-F]{64})\b", checksum_line)
    if not match:
        raise RuntimeError(
            f"SHA256 checksum not found in entry: {checksum_line}"
        )

    expected_checksum = match.group(1)
    return checksum_valid(file_path, expected_checksum)


def checksum_valid(file_path: str, expected_checksum: str) -> bool:
    """Verify the SHA256 checksum of a remote file.

    Args:
        file_path: Remote path to the file.
        expected_checksum: The expected 64-character hex SHA256 string.

    Returns:
        True if the file's checksum matches *expected_checksum*.
    """
    server = get_target("server")
    cmd = f"sha256sum -b {file_path} | awk '{{print $1}}'"
    file_checksum, _code = server.run(cmd, runs_in_container=False)
    return file_checksum.strip() == expected_checksum


def devel_repo(repo_url: str) -> bool:
    """Return True if *repo_url* looks like a development repository URL.

    A URL is considered a development repo when it contains 'devel',
    'totest', or 'systemsmanagement' but does NOT contain 'sle-module'.

    Args:
        repo_url: The repository URL to inspect.

    Returns:
        True if the URL matches the development-repo heuristic.
    """
    url = repo_url.lower()
    is_devel = (
        "devel" in url
        or "totest" in url
        or "systemsmanagement" in url
    )
    return is_devel and "sle-module" not in url
