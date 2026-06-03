# Copyright (c) 2024-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/support/remote_node.rb.

Provides the RemoteNode class for interacting with remote test nodes via SSH,
along with module-level registries used across the testsuite.
"""

import os
import re

from support.env import DEFAULT_TIMEOUT, PRIVATE_NET
from support.constants import ENV_VAR_BY_HOST, PRIVATE_ADDRESSES
from support.network_utils import ssh_command, scp_upload_command, scp_download_command
from support.commonlib import repeat_until_timeout

# Module-level registries — populated during RemoteNode.__init__
node_by_host: dict = {}
host_by_node: dict = {}
named_nodes: dict = {}


def _net_prefix():
    """Return the private network prefix (e.g. '192.168.1.') from PRIVATE_NET."""
    if not PRIVATE_NET:
        return None
    return re.sub(r"\.0+/24$", ".", PRIVATE_NET)


class RemoteNode:
    """Represents a remote node accessible via SSH."""

    def __init__(self, host: str, port: int = 22):
        self.host = host
        self.port = port
        self.hostname = ""
        self.full_hostname = ""
        self.target = ""
        self.os_family = ""
        self.os_version = ""
        self.local_os_family = ""
        self.local_os_version = ""
        self.has_mgrctl = False
        self.has_kubectl = False
        self.private_ip = None
        self.public_ip = None
        self.private_interface = None
        self.public_interface = None

        print(f"Initializing a remote node for '{self.host}'.")
        if host not in ENV_VAR_BY_HOST:
            raise NotImplementedError(
                f"Host {host} is not defined as a valid host in the Test Framework.")

        env_var = ENV_VAR_BY_HOST[host]
        if env_var not in os.environ:
            print(f"Warning: Host {host} is not defined as environment variable.")
            return

        self.target = os.environ[env_var].strip()

        # Remove /etc/motd so SSH output is not polluted
        if host != "localhost":
            self.ssh("rm -f /etc/motd && touch /etc/motd", host=self.target)

        out, _err, _code = self.ssh("echo $HOSTNAME", host=self.target)
        self.hostname = out.strip()
        if not self.hostname:
            raise ConnectionError(f"We can't connect to {host} through SSH.")

        named_nodes[host] = self.hostname

        if host == "server":
            _, _, code = self.ssh("which mgrctl", host=self.target)
            self.has_mgrctl = (code == 0)
            _, _, code = self.ssh("which kubectl", host=self.target)
            self.has_kubectl = (code == 0)

        if host == "server" and not self.has_kubectl:
            # Remove /etc/motd inside the container too
            self.run("rm -f /etc/motd && touch /etc/motd")
            out, code = self.run(
                r"sed -n 's/^java\.hostname *= *\(.\+\)$/\1/p' /etc/rhn/rhn.conf")
        else:
            out, _err, code = self.ssh("hostname -f", host=self.target)

        self.full_hostname = out.strip()
        if not self.full_hostname:
            raise RuntimeError(
                f"No FQDN for '{self.hostname}'. Response code: {code}")

        print(f"Host '{host}' is alive with hostname {self.hostname} "
              f"and FQDN {self.full_hostname}")

        # Determine OS version/family both inside and outside the container
        self.os_version, self.os_family = self._get_os_version(runs_in_container=True)
        self.local_os_version, self.local_os_family = self._get_os_version(
            runs_in_container=False)

        if host in PRIVATE_ADDRESSES and PRIVATE_NET:
            prefix = _net_prefix()
            self.private_ip = prefix + PRIVATE_ADDRESSES[host]
            self.private_interface = None
            for dev in ["eth1", "ens4"]:
                _out, code = self.run_local(
                    f"ip address show dev {dev}", check_errors=False)
                if code == 0:
                    self.private_interface = dev
                    break
            if self.private_interface is None:
                raise RuntimeError(f"No private interface for '{self.hostname}'.")

        ip = self._client_public_ip()
        if ip:
            self.public_ip = ip

        node_by_host[host] = self
        host_by_node[id(self)] = host

    # ------------------------------------------------------------------
    # Low-level SSH / SCP primitives
    # ------------------------------------------------------------------

    def ssh(self, command: str, host: str = None):
        """Run a raw SSH command. Returns (stdout, stderr, exit_code)."""
        target = host if host is not None else self.full_hostname
        return ssh_command(command, target, port=self.port)

    def scp_upload(self, local_path: str, remote_path: str, host: str = None):
        """Upload a file to the remote node via SFTP."""
        target = host if host is not None else self.full_hostname
        scp_upload_command(local_path, remote_path, target, port=self.port)

    def scp_download(self, remote_path: str, local_path: str, host: str = None):
        """Download a file from the remote node via SFTP."""
        target = host if host is not None else self.full_hostname
        scp_download_command(remote_path, local_path, target, port=self.port)

    # ------------------------------------------------------------------
    # run() — wraps with mgrctl exec when running inside a container
    # ------------------------------------------------------------------

    def run(self, cmd: str, *, runs_in_container: bool = True,
            separated_results: bool = False, check_errors: bool = True,
            timeout: int = DEFAULT_TIMEOUT, successcodes: list = None,
            buffer_size: int = 65536, verbose: bool = False,
            exec_option: str = "-i"):
        """
        Run a command on this node.

        When self.has_mgrctl and runs_in_container, wraps the command with
        'mgrctl exec {exec_option} ...' so it executes inside the container.
        """
        if successcodes is None:
            successcodes = [0]
        if self.has_mgrctl and runs_in_container:
            escaped = cmd.replace("'", "'\"'\"'")
            cmd = f"mgrctl exec {exec_option} '{escaped}'"
        return self.run_local(
            cmd, separated_results=separated_results,
            check_errors=check_errors, timeout=timeout,
            successcodes=successcodes, buffer_size=buffer_size,
            verbose=verbose)

    # ------------------------------------------------------------------
    # run_pipe() — runs pipe-chained commands and validates PIPESTATUS
    # ------------------------------------------------------------------

    def run_pipe(self, cmd: str, expected_pipestatus_codes: list, *,
                 runs_in_container: bool = True, separated_results: bool = False,
                 check_errors: bool = True, timeout: int = DEFAULT_TIMEOUT,
                 successcodes: list = None, buffer_size: int = 65536,
                 verbose: bool = False, exec_option: str = "-i"):
        """
        Run a pipe-chained command and validate per-command exit codes via PIPESTATUS.

        Appends '${PIPESTATUS[*]}' capture to the command, then reads it back.
        Raises if the actual pipestatus array does not match expected_pipestatus_codes
        (when check_errors is True).
        """
        if successcodes is None:
            successcodes = [0]
        pipestatus_file = "/tmp/temp_file_with_stderrs"
        cmd_with_capture = f"{cmd}; echo ${{PIPESTATUS[*]}} > {pipestatus_file}"
        cmd_read_codes = f"cat {pipestatus_file}; rm {pipestatus_file}"

        if self.has_mgrctl and runs_in_container:
            escaped_cmd = cmd_with_capture.replace("'", "'\"'\"'")
            escaped_read = cmd_read_codes.replace("'", "'\"'\"'")
            cmd_with_capture = f"mgrctl exec {exec_option} '{escaped_cmd}'"
            cmd_read_codes = f"mgrctl exec {exec_option} '{escaped_read}'"

        out, initial_code = self.run_local(
            cmd_with_capture, separated_results=False,
            check_errors=check_errors, timeout=timeout,
            successcodes=successcodes, buffer_size=buffer_size,
            verbose=verbose)

        pipestatus_out, _code = self.run_local(cmd_read_codes)
        pipestatus_array = [int(x) for x in pipestatus_out.split()]

        if len(expected_pipestatus_codes) != len(pipestatus_array):
            raise RuntimeError(
                f"Expected number of pipestatus codes does not match number of "
                f"commands chained by pipes. "
                f"Expected: {expected_pipestatus_codes}, Got: {pipestatus_array}")

        if check_errors and any(
                pipestatus_array[i] != expected_pipestatus_codes[i]
                for i in range(len(pipestatus_array))):
            raise RuntimeError(
                f"Expected outcome does not match with current outcome. "
                f"Expected pipestatus: {expected_pipestatus_codes}, "
                f"Got: {pipestatus_array}")

        if separated_results:
            return out, pipestatus_out, initial_code
        return out + pipestatus_out, initial_code

    # ------------------------------------------------------------------
    # run_local() — always SSH to self.target (no container wrapping)
    # ------------------------------------------------------------------

    def run_local(self, cmd: str, *, separated_results: bool = False,
                  check_errors: bool = True, timeout: int = DEFAULT_TIMEOUT,
                  successcodes: list = None, buffer_size: int = 65536,
                  verbose: bool = False):
        """
        Run a command on self.target via SSH without any container wrapping.

        Returns (stdout+stderr, exit_code) by default, or
        (stdout, stderr, exit_code) when separated_results=True.
        """
        if successcodes is None:
            successcodes = [0]
        stdout, stderr, code = ssh_command(
            cmd, self.target, port=self.port,
            timeout=timeout, buffer_size=buffer_size)

        # Strip ANSI color codes (matches Ruby: gsub(/\e\[([;\d]+)?m/, ''))
        out_nocolor = re.sub(r"\x1b\[[\d;]*m", "", stdout)

        if check_errors and code not in successcodes:
            raise RuntimeError(
                f"FAIL: {cmd} returned status code = {code}.\n"
                f"Output:\n{out_nocolor}")

        if verbose:
            print(f"{cmd} returned status code = {code}.\nOutput:\n'{out_nocolor}'")

        if separated_results:
            return stdout, stderr, code
        return stdout + stderr, code

    # ------------------------------------------------------------------
    # Polling helpers
    # ------------------------------------------------------------------

    def run_until_ok(self, cmd: str, *, timeout: int = DEFAULT_TIMEOUT,
                     runs_in_container: bool = True):
        """Run cmd repeatedly until it exits with code 0 or timeout elapses."""
        def attempt():
            result, code = self.run(
                cmd, runs_in_container=runs_in_container, check_errors=False)
            if code == 0:
                return result, code
            return None

        return repeat_until_timeout(
            attempt, timeout=timeout, report_result=True,
            message=f"Command did not succeed: {cmd}")

    def run_until_fail(self, cmd: str, *, timeout: int = DEFAULT_TIMEOUT,
                       runs_in_container: bool = True):
        """Run cmd repeatedly until it exits with a non-zero code or timeout elapses."""
        def attempt():
            result, code = self.run(
                cmd, runs_in_container=runs_in_container, check_errors=False)
            if code != 0:
                return result, code
            return None

        return repeat_until_timeout(
            attempt, timeout=timeout, report_result=True,
            message=f"Command did not fail: {cmd}")

    def wait_while_process_running(self, process: str):
        """Block until the named process is no longer running."""
        def attempt():
            result, code = self.run(
                f"pgrep -x {process} >/dev/null", check_errors=False)
            if code != 0:
                return result, code
            return None

        return repeat_until_timeout(
            attempt, report_result=True,
            message=f"Process still running: {process}")

    def wait_until_online(self, timeout: int = DEFAULT_TIMEOUT):
        """Block until the node responds to SSH."""
        def attempt():
            try:
                out, _err, code = self.ssh("echo ok", host=self.target)
                if code == 0 and "ok" in out:
                    return True
            except Exception:
                pass
            return None

        repeat_until_timeout(attempt, timeout=timeout,
                             message=f"Node {self.host} did not come back online "
                                     f"within {timeout} seconds.")
        print(f"Node {self.hostname} is online.")

    def wait_until_offline(self):
        """Block until the node stops responding to SSH."""
        import time
        while not self.node_offline():
            time.sleep(1)
        print(f"Node {self.hostname} is offline.")

    # ------------------------------------------------------------------
    # File / folder operations
    # ------------------------------------------------------------------

    def inject(self, test_runner_file: str, remote_node_file: str):
        """
        Copy a file from the test runner (controller) into this remote node.

        When mgrctl is available, stages via /tmp then uses 'mgrctl cp'.
        """
        from support.remote_nodes_env import get_target
        localhost = get_target("localhost")
        if self.has_mgrctl:
            import os as _os
            tmp_file = f"/tmp/{_os.path.basename(test_runner_file)}"
            localhost.scp_upload(test_runner_file, tmp_file, host=self.full_hostname)
            _out, code = self.run_local(f"mgrctl cp {tmp_file} server:{remote_node_file}")
            if code != 0:
                raise RuntimeError(f"Failed to copy {tmp_file} to container")
        else:
            localhost.scp_upload(test_runner_file, remote_node_file,
                                 host=self.full_hostname)

    def extract(self, remote_node_file: str, test_runner_file: str):
        """
        Copy a file from this remote node into the test runner (controller).

        When mgrctl is available, uses 'mgrctl cp' then downloads from /tmp.
        """
        from support.remote_nodes_env import get_target
        localhost = get_target("localhost")
        if self.has_mgrctl:
            import os as _os
            tmp_file = f"/tmp/{_os.path.basename(remote_node_file)}"
            _out, code = self.run_local(
                f"mgrctl cp server:{remote_node_file} {tmp_file}", verbose=False)
            if code != 0:
                raise RuntimeError(f"Failed to extract {remote_node_file} from container")
            localhost.scp_download(tmp_file, test_runner_file, host=self.full_hostname)
        else:
            localhost.scp_download(remote_node_file, test_runner_file,
                                   host=self.full_hostname)

    def file_exists(self, path: str) -> bool:
        """Return True if path is a regular file on this node."""
        if self.has_mgrctl:
            _out, code = self.run_local(
                f"mgrctl exec -- 'test -f {path}'", check_errors=False)
        else:
            _out, _err, code = self.ssh(f"test -f {path}")
        return code == 0

    def folder_exists(self, path: str) -> bool:
        """Return True if path is a directory on this node."""
        if self.has_mgrctl:
            _out, code = self.run_local(
                f"mgrctl exec -- 'test -d {path}'", check_errors=False)
        else:
            _out, _err, code = self.ssh(f"test -d {path}")
        return code == 0

    def file_delete(self, path: str) -> int:
        """Delete a file on this node. Returns the exit code."""
        if self.has_mgrctl:
            _out, code = self.run_local(
                f"mgrctl exec -- 'rm {path}'", check_errors=False)
        else:
            _out, _err, code = self.ssh(f"rm {path}")
        return code

    def folder_delete(self, path: str) -> int:
        """Recursively delete a directory on this node. Returns the exit code."""
        if self.has_mgrctl:
            _out, code = self.run_local(
                f"mgrctl exec -- 'rm -rf {path}'", check_errors=False)
        else:
            _out, _err, code = self.ssh(f"rm -rf {path}")
        return code

    # ------------------------------------------------------------------
    # Node state helpers
    # ------------------------------------------------------------------

    def node_offline(self) -> bool:
        """Return True if the node does not respond to a quick SSH echo."""
        result, _code = self.run_local("echo test", timeout=1, check_errors=False)
        return not result or not result.strip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_os_version(self, *, runs_in_container: bool = True):
        """
        Determine (os_version, os_family) by reading /etc/os-release.

        Mirrors the Ruby implementation including macOS, SLES 16 VARIANT,
        and the SLES SP version rewrite (e.g. '15.3' → '15-SP3').

        Returns (None, None) when the information cannot be determined.
        """
        # Try ID= from /etc/os-release
        os_family_raw, code = self.run(
            "grep '^ID=' /etc/os-release",
            runs_in_container=runs_in_container, check_errors=False)
        if code != 0:
            # Fall back to macOS sw_vers
            os_family_raw, code = self.run(
                "sw_vers --productName",
                runs_in_container=runs_in_container, check_errors=False)
        if code != 0:
            return None, None

        os_family = os_family_raw.strip()
        if os_family != "macOS":
            parts = os_family.split("=", 1)
            if len(parts) < 2:
                return None, None
            os_family = parts[1]
        if not os_family:
            return None, None
        os_family = os_family.strip('"')

        if os_family == "macOS":
            os_version_raw, code = self.run(
                "sw_vers --productVersion",
                runs_in_container=runs_in_container, check_errors=False)
            if code != 0:
                return None, None
            os_version = os_version_raw.strip()
        else:
            os_version_raw, code = self.run(
                "grep '^VERSION_ID=' /etc/os-release",
                runs_in_container=runs_in_container, check_errors=False)
            if code != 0:
                return None, None
            parts = os_version_raw.strip().split("=", 1)
            if len(parts) < 2:
                return None, None
            os_version = parts[1]
            if not os_version:
                return None, None
        os_version = os_version.strip('"')

        # SLES 16 — check for Micro variant
        if re.match(r"^sles", os_family):
            if re.match(r"^16", os_version):
                os_variant_raw, code = self.run(
                    "grep '^VARIANT=' /etc/os-release",
                    runs_in_container=runs_in_container, check_errors=False)
                if code != 0:
                    return None, None
                os_variant = os_variant_raw.strip()
                parts = os_variant.split("=", 1)
                if len(parts) < 2:
                    return None, None
                os_variant = parts[1].strip('"')
                if os_variant == "Micro":
                    os_family = "sle-micro"
                    os_ver_raw, code = self.run(
                        "grep '^SUSE_SUPPORT_PRODUCT_VERSION=' /etc/os-release",
                        runs_in_container=runs_in_container, check_errors=False)
                    if code != 0:
                        return None, None
                    parts = os_ver_raw.strip().split("=", 1)
                    if len(parts) < 2:
                        return None, None
                    os_version = parts[1].strip('"')
                    if not os_version:
                        return None, None
            else:
                # On older SLES: '15.3' → '15-SP3'
                os_version = os_version.replace(".", "-SP")

        print(f"Node: {self.hostname}, OS Version: {os_version}, Family: {os_family}")
        return os_version, os_family

    def _client_public_ip(self) -> str:
        """
        Detect the public IP address of this node.

        Handles both macOS (ipconfig getifaddr) and Linux (ip address show).
        Raises ArgumentError if no interface can be resolved.
        """
        if self.os_family == "macOS":
            for dev in ["en0", "en1", "en2", "en3", "en4", "en5", "en6", "en7"]:
                output, code = self.run_local(
                    f"ipconfig getifaddr {dev}", check_errors=False)
                if code != 0:
                    continue
                self.public_interface = dev
                return output.strip() if output.strip() else ""
        else:
            for dev in ["br0", "eth0", "eth1", "eth1000",
                        "ens0", "ens1", "ens2", "ens3", "ens4",
                        "ens5", "ens6", "ens7"]:
                output, code = self.run_local(
                    f"ip address show dev {dev} | grep 'inet '",
                    check_errors=False)
                if code != 0:
                    continue
                self.public_interface = dev
                if not output.strip():
                    return ""
                # Parse: 'inet 1.2.3.4/24 ...' → '1.2.3.4'
                parts = output.split()
                if len(parts) >= 2:
                    return parts[1].split("/")[0]
                return ""
        raise ValueError(f"Cannot resolve public ip of {self.host}")
