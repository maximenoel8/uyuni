# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/security_steps.rb.

Covers URI and SSL integrity steps: static resource retrieval and
HTTP response header assertions.
"""

import ssl
import urllib.request
import urllib.error

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target


# Static resource map (mirrors Ruby STATIC_RESOURCES hash)
_STATIC_RESOURCES = {
    "img": "action-add.gif",
    "css": "susemanager-sp-migration.css",
    "fonts": "DroidSans.ttf",
    "javascript": "actionchain.js",
}


@when(parsers.re(r'I retrieve a "(?P<resource_type>.*)" static resource'))
def step_retrieve_static_resource(resource_type: str, context_store):
    import os
    app_host = os.environ.get("APP_HOST", "")
    url = f"{app_host}/{resource_type}/{_STATIC_RESOURCES[resource_type]}"
    context_store["current_url"] = url

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, context=ctx) as resp:
        # Collect all response headers as a dict with lowercase keys
        headers = {k.lower(): v for k, v in resp.headers.items()}
        context_store["response_headers"] = headers


@then(parsers.re(r'the response header "(?P<name>.*?)" should be "(?P<value>.*?)"'))
def step_response_header_should_be(name: str, value: str, context_store):
    headers = context_store.get("response_headers", {})
    url = context_store.get("current_url", "")
    assert name.lower() in headers, f"Header '{name}' not present in '{url}'"
    assert headers[name.lower()] == value, \
        f"Header '{name}' in '{url}' is not '{value}', got '{headers[name.lower()]}'"


@then(parsers.re(r'the response header "(?P<name>.*?)" should not be "(?P<value>.*?)"'))
def step_response_header_should_not_be(name: str, value: str, context_store):
    headers = context_store.get("response_headers", {})
    assert headers.get(name.lower()) != value, \
        f"Header '{name}' in '{context_store.get('current_url', '')}' is '{value}'"


@then(parsers.re(r'the response header "(?P<name>.*?)" should contain "(?P<value>.*?)"'))
def step_response_header_should_contain(name: str, value: str, context_store):
    headers = context_store.get("response_headers", {})
    url = context_store.get("current_url", "")
    assert name.lower() in headers, f"Header '{name}' not present in '{url}'"
    assert value in headers[name.lower()], \
        f"Header '{name}' in '{url}' does not contain '{value}'"


@then(parsers.re(r'the response header "(?P<name>.*?)" should not be present'))
def step_response_header_should_not_be_present(name: str, context_store):
    headers = context_store.get("response_headers", {})
    url = context_store.get("current_url", "")
    assert name.lower() not in headers, f"Header '{name}' present in '{url}'"
