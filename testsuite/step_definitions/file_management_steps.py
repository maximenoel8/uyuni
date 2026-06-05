# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/file_management_steps.rb.

Covers file management steps: create/destroy directories, file existence
checks, content injection, and bootstrap script execution.
"""

import os

from pytest_bdd import given, when, then, parsers

from support.file_management import file_inject, file_extract, generate_temp_file
from support.remote_nodes_env import get_target, get_system_name
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Directory management
# ---------------------------------------------------------------------------

@when(parsers.re(r'I destroy "(?P<directory>[^"]*)" directory on server'))
def step_destroy_directory_on_server(directory: str):
    get_target("server").run(f"rm -rf {directory}")


@when(parsers.re(r'I destroy "(?P<directory>[^"]*)" directory on "(?P<host>[^"]*)"'))
def step_destroy_directory_on_host(directory: str, host: str):
    node = get_target(host)
    node.run(f"rm -rf {directory}")


# ---------------------------------------------------------------------------
# File removal
# ---------------------------------------------------------------------------

@when(parsers.re(r'I remove "(?P<filename>[^"]*)" from "(?P<host>[^"]*)"'))
def step_remove_file_from_host(filename: str, host: str):
    from support.file_management import file_delete
    node = get_target(host)
    file_delete(node, filename)


# ---------------------------------------------------------------------------
# File existence checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'file "(?P<filename>[^"]*)" should exist on server'))
def step_file_should_exist_on_server(filename: str):
    get_target("server").run(f"test -f {filename}")


@then(parsers.re(r'file "(?P<filename>[^"]*)" should exist on "(?P<host>[^"]*)"'))
def step_file_should_exist_on_host(filename: str, host: str):
    node = get_target(host)
    node.run(f"test -f {filename}")


@then(parsers.re(
    r'file "(?P<filename>[^"]*)" should have (?P<permissions>[0-9]+) permissions on "(?P<host>[^"]*)"'
))
def step_file_should_have_permissions(filename: str, permissions: str, host: str):
    node = get_target(host)
    node.run(f'test "`stat -c \'%a\' {filename}`" = "{permissions}"')


@then(parsers.re(r'file "(?P<filename>[^"]*)" should not exist on server'))
def step_file_should_not_exist_on_server(filename: str):
    get_target("server").run(f"test ! -f {filename}")


@then(parsers.re(r'file "(?P<filename>[^"]*)" should not exist on "(?P<host>[^"]*)"'))
def step_file_should_not_exist_on_host(filename: str, host: str):
    node = get_target(host)
    node.run(f"test ! -f {filename}")


# ---------------------------------------------------------------------------
# File content steps
# ---------------------------------------------------------------------------

@when(parsers.re(r'I store "(?P<content>[^"]*)" into file "(?P<filename>[^"]*)" on "(?P<host>[^"]*)"'))
def step_store_content_into_file(content: str, filename: str, host: str):
    node = get_target(host)
    node.run(f'echo "{content}" > {filename}', timeout=600)


@then(parsers.re(
    r'file "(?P<filename>[^"]*)" should contain "(?P<content>[^"]*)" on "(?P<host>[^"]*)"'
))
def step_file_should_contain(filename: str, content: str, host: str):
    node = get_target(host)
    node.run(f"test -f {filename}")
    node.run(f'grep "{content}" {filename}')


# ---------------------------------------------------------------------------
# Bootstrap script
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I bootstrap "(?P<host>[^"]*)" using bootstrap script with activation key "(?P<key>[^"]*)" '
    r'from the (?P<target_type>server|proxy)'
))
def step_bootstrap_using_bootstrap_script(host: str, key: str, target_type: str):
    from support.commonlib import deb_host, rh_host

    # Choose target: use server if proxy is not defined or target_type is server
    if target_type == "server":
        target = get_target("server")
    else:
        proxy = get_target("proxy")
        if proxy is None:
            target = get_target("server")
        else:
            target = proxy

    use_salt_bundle = os.environ.get("USE_SALT_BUNDLE", "false").lower() == "true"
    force_bundle = "--force-bundle" if use_salt_bundle else ""

    node = get_target(host)
    gpg_keys = _get_gpg_keys(node, target)
    cmd = (
        f"mgr-bootstrap {force_bundle} && "
        f"sed -i s'/^exit 1//' /srv/www/htdocs/pub/bootstrap/bootstrap.sh && "
        f"sed -i '/^ACTIVATION_KEYS=/c\\ACTIVATION_KEYS={key}' /srv/www/htdocs/pub/bootstrap/bootstrap.sh && "
        f"chmod 644 /srv/www/htdocs/pub/RHN-ORG-TRUSTED-SSL-CERT && "
        f"sed -i '/^ORG_GPG_KEY=/c\\ORG_GPG_KEY={','.join(gpg_keys)}' /srv/www/htdocs/pub/bootstrap/bootstrap.sh && "
        "cat /srv/www/htdocs/pub/bootstrap/bootstrap.sh"
    )
    output, _code = target.run(cmd, verbose=True)
    if key not in output:
        raise RuntimeError(f"Key: {key} not included")

    bootstrap_script = "bootstrap-general.exp"
    source = os.path.join(
        os.path.dirname(__file__), f"../features/upload_files/{bootstrap_script}"
    )
    dest = f"/tmp/{bootstrap_script}"
    success = file_inject(target, source, dest)
    assert success, "File injection failed"

    system_name = get_system_name(host)
    has_mgrctl = getattr(target, "has_mgrctl", False)
    output, _code = target.run_local(
        f"sed -i '/^set timeout /c\\set timeout {DEFAULT_TIMEOUT}' /tmp/{bootstrap_script} && "
        f"expect -f /tmp/{bootstrap_script} {system_name} {has_mgrctl}",
        verbose=True
    )
    if "-bootstrap complete-" not in output:
        raise RuntimeError("Bootstrap didn't finish properly")


# ---------------------------------------------------------------------------
# Hosts file
# ---------------------------------------------------------------------------

@when(parsers.re(r'I remove server hostname from hosts file on "(?P<host>[^"]*)"'))
def step_remove_server_hostname_from_hosts(host: str):
    server_hostname = get_target("server").full_hostname
    node = get_target(host)
    node.run(f"sed -i 's/{server_hostname}//' /etc/hosts")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_gpg_keys(node, target) -> list:
    """Get GPG key filenames relevant to the node's OS family."""
    os_family = node.os_family
    keys = []
    try:
        output, _code = target.run(
            "ls /srv/www/htdocs/pub/*.key 2>/dev/null", check_errors=False
        )
        for line in output.splitlines():
            key_file = os.path.basename(line.strip())
            if key_file:
                keys.append(key_file)
    except Exception:
        pass
    return keys if keys else [""]
