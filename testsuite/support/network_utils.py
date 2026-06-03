# Copyright (c) 2026 SUSE LLC.
# Licensed under the terms of the MIT license.

import os
import time
import paramiko

from support.env import DEFAULT_TIMEOUT


def _build_ssh_config(host: str) -> dict:
    config = paramiko.SSHConfig()
    cfg_path = os.path.expanduser("~/.ssh/config")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            config.parse(f)
    return config.lookup(host)


def _make_connect_kwargs(cfg: dict, host: str, port: int, timeout: int) -> dict:
    kwargs = dict(
        hostname=cfg.get("hostname", host),
        port=int(cfg.get("port", port)),
        username=cfg.get("user", "root"),
        timeout=min(timeout, 30),
        look_for_keys=True,
        allow_agent=True,
        banner_timeout=30,
    )
    if "identityfile" in cfg:
        key_path = os.path.expanduser(cfg["identityfile"][0])
        if os.path.exists(key_path):
            kwargs["key_filename"] = key_path
    return kwargs


def ssh_command(command: str, host: str, *, port: int = 22,
                timeout: int = DEFAULT_TIMEOUT, buffer_size: int = 65536):
    """Execute a command via SSH. Returns (stdout, stderr, exit_code)."""
    cfg = _build_ssh_config(host)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(**_make_connect_kwargs(cfg, host, port, timeout))
        channel = client.get_transport().open_session()
        channel.settimeout(timeout)
        channel.exec_command(command)

        stdout_chunks = []
        stderr_chunks = []
        while True:
            if channel.recv_ready():
                data = channel.recv(buffer_size)
                if data:
                    stdout_chunks.append(data.decode("utf-8", errors="replace"))
            if channel.recv_stderr_ready():
                data = channel.recv_stderr(buffer_size)
                if data:
                    stderr_chunks.append(data.decode("utf-8", errors="replace"))
            if channel.exit_status_ready():
                while channel.recv_ready():
                    data = channel.recv(buffer_size)
                    if data:
                        stdout_chunks.append(data.decode("utf-8", errors="replace"))
                while channel.recv_stderr_ready():
                    data = channel.recv_stderr(buffer_size)
                    if data:
                        stderr_chunks.append(data.decode("utf-8", errors="replace"))
                break
            time.sleep(0.1)

        exit_code = channel.recv_exit_status()
        return "".join(stdout_chunks), "".join(stderr_chunks), exit_code
    finally:
        client.close()


def scp_upload_command(local_path: str, remote_path: str, host: str, *,
                       port: int = 22, timeout: int = DEFAULT_TIMEOUT):
    """Upload a file to a remote host via SFTP."""
    cfg = _build_ssh_config(host)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(**_make_connect_kwargs(cfg, host, port, timeout))
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        client.close()


def scp_download_command(remote_path: str, local_path: str, host: str, *,
                         port: int = 22, timeout: int = DEFAULT_TIMEOUT):
    """Download a file from a remote host via SFTP."""
    cfg = _build_ssh_config(host)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(**_make_connect_kwargs(cfg, host, port, timeout))
        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
    finally:
        client.close()


try:
    import datetime
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    def generate_dummy_cacert(filename: str,
                              subject: str = "/DC=localdomain/DC=localhost/CN=dummy CA"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([
            x509.NameAttribute(NameOID.DOMAIN_COMPONENT, "localdomain"),
            x509.NameAttribute(NameOID.DOMAIN_COMPONENT, "localhost"),
            x509.NameAttribute(NameOID.COMMON_NAME, "dummy CA"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        with open(filename, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

    def get_dummy_cacert(filename: str) -> str:
        with open(filename) as f:
            return f.read()

except ImportError:
    def generate_dummy_cacert(filename, subject=None):
        raise NotImplementedError("cryptography package not installed")

    def get_dummy_cacert(filename):
        raise NotImplementedError("cryptography package not installed")
