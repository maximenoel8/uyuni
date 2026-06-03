# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/https_connection_steps.rb.

Covers HTTPS connection checks: redirect, secured connection,
certificate validation, page title checks.
"""

import ssl
import socket
import urllib.request
import urllib.error

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target


# ---------------------------------------------------------------------------
# Connection steps
# ---------------------------------------------------------------------------

@when("I connect to the server insecurely")
def step_connect_to_server_insecurely(page, context_store):
    import os
    app_host = os.environ.get("APP_HOST", "")
    http_url = app_host.replace("https:", "http:")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(http_url)
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            context_store["uri_open_result"] = resp
            context_store["uri_open_status"] = resp.status
    except urllib.error.HTTPError as e:
        context_store["error"] = e
        context_store["error_message"] = str(e.code)
    except Exception as e:
        context_store["error"] = e
        context_store["error_message"] = str(e)


@then("the connection should redirect to the secured channel")
def step_connection_should_redirect(context_store):
    error = context_store.get("error")
    error_message = context_store.get("error_message", "")
    # Accept either an HTTPError 302 or an SSLError as valid redirect indicators
    valid_redirect = False
    if error is not None:
        if isinstance(error, urllib.error.HTTPError) and error.code == 302:
            valid_redirect = True
        elif isinstance(error, ssl.SSLError):
            valid_redirect = True
        elif "302" in error_message:
            valid_redirect = True
    assert valid_redirect, "The connection has not redirected to the secure channel!"


@when("I connect to the server securely")
def step_connect_to_server_securely(context_store):
    import os
    app_host = os.environ.get("APP_HOST", "")
    https_url = app_host.replace("http:", "https:")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(https_url, context=ctx, timeout=5) as resp:
        content = resp.read().decode("utf-8", errors="replace")
        context_store["uri_open_result"] = resp
        context_store["uri_open_status"] = resp.status
        # Extract page title
        import re
        match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        context_store["htmldoc_title"] = match.group(1).strip() if match else ""


@then("the connection should be secured")
def step_connection_should_be_secured(context_store):
    status = context_store.get("uri_open_status")
    assert status == 200, f"The return value is not OK (not code 200), got: {status}"


@then(parsers.re(r'the page title should contain "(?P<page_title>.*?)" text'))
def step_page_title_should_contain(page_title: str, context_store):
    htmldoc_title = context_store.get("htmldoc_title", "")
    import re
    assert re.search(f".+{re.escape(page_title)}", htmldoc_title), \
        f"The page title '{htmldoc_title}' does not match '{page_title}'"


@when("I connect to the server securely while using CA certificate file")
def step_connect_securely_with_ca_cert(context_store):
    import os
    app_host = os.environ.get("APP_HOST", "")
    https_url = app_host.replace("http:", "https:")
    hostname = https_url.replace("https://", "")
    ssl_ca_cert_file = f"/etc/ssl/certs/{hostname}.pem"
    try:
        ctx = ssl.create_default_context(cafile=ssl_ca_cert_file)
        with urllib.request.urlopen(https_url, context=ctx, timeout=5) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            context_store["uri_open_result"] = resp
            context_store["uri_open_status"] = resp.status
            import re
            match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            context_store["htmldoc_title"] = match.group(1).strip() if match else ""
    except Exception as e:
        context_store["error"] = e
        context_store["error_message"] = str(e)


@when("I connect to the server securely while using incorrect certificate as a CA certificate file")
def step_connect_securely_with_wrong_ca_cert(context_store):
    import os
    ssl_cacert_file = "/tmp/dummy_CA.pem"
    _generate_dummy_cacert(ssl_cacert_file, "/DC=localdomain/DC=localhost/CN=dummy https test CA")
    context_store["ssl_cacert_file"] = ssl_cacert_file
    app_host = os.environ.get("APP_HOST", "")
    https_url = app_host.replace("http:", "https:")
    try:
        ctx = ssl.create_default_context(cafile=ssl_cacert_file)
        # VERIFY_PEER with wrong cert — should fail
        with urllib.request.urlopen(https_url, context=ctx, timeout=5) as resp:
            context_store["uri_open_result"] = resp
    except Exception as e:
        context_store["error"] = e
        context_store["error_message"] = str(e)


@then("the secure connection should fail due to unverified certificate signature")
def step_secure_connection_should_fail(context_store):
    error = context_store.get("error")
    assert error is not None and context_store.get("error_message"), \
        "Connection passed unexpectedly!"
    assert isinstance(error, ssl.SSLError), \
        f"Unexpected connection error type: {type(error).__name__}: {error}"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _generate_dummy_cacert(filepath: str, subject: str):
    """Generate a self-signed dummy CA certificate using openssl CLI."""
    import subprocess
    subprocess.run(
        [
            "openssl", "req", "-new", "-x509", "-newkey", "rsa:2048",
            "-keyout", "/dev/null", "-out", filepath,
            "-days", "1", "-nodes", "-subj", subject,
        ],
        check=True,
        capture_output=True,
    )
