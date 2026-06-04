# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/content_lifecycle_steps.rb.

Covers content lifecycle management steps: environment building, promoting,
SSH key management, calendar files, Ansible playbooks, and reactivation keys.
"""

import os

from pytest_bdd import given, when, then, parsers

from support.commonlib import check_text, click_button_and_wait, wait_for_ajax, repeat_until_timeout
from support.remote_nodes_env import get_target, get_system_name
from support.env import DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# Content lifecycle environment management
# ---------------------------------------------------------------------------

@when("I click the environment build button")
def step_click_environment_build_button(page):
    page.locator("button#cm-build-modal-save-button:not([disabled])").wait_for(
        timeout=DEFAULT_TIMEOUT * 1000
    )
    page.locator("button#cm-build-modal-save-button").click()


@when("I click promote from Development to QA")
def step_click_promote_development_to_qa(page):
    promote_buttons = page.get_by_role("button", name="Promote")
    assert promote_buttons.first.count(), "No Promote button found"
    promote_buttons.first.click()


@when("I click promote from QA to Production")
def step_click_promote_qa_to_production(page):
    promote_buttons = page.get_by_role("button", name="Promote").all()
    assert len(promote_buttons) >= 2, "Expected at least 2 Promote buttons"
    promote_buttons[1].click()


@then(parsers.re(r'I should see a "(?P<text>[^"]*)" text in the environment "(?P<env>[^"]*)"'))
def step_should_see_text_in_environment(page, text: str, env: str):
    container = page.locator(f"xpath=//h3[text()='{env}']/../..")
    assert container.get_by_text(text).count(), f'Text "{text}" not found in environment {env}'


@when(parsers.re(
    r'I wait at most (?P<seconds>\d+) seconds until I see "(?P<text>[^"]*)" '
    r'text in the environment "(?P<env>[^"]*)"'
))
def step_wait_until_see_text_in_environment(page, seconds: str, text: str, env: str):
    container = page.locator(f"xpath=//h3[text()='{env}']/../..")

    def _has_text():
        if container.get_by_text(text).count():
            return True
        return None

    repeat_until_timeout(_has_text, timeout=int(seconds),
                         message=f'Text "{text}" not found in environment {env}')


@when(parsers.re(
    r'I wait until I see "(?P<text>[^"]*)" text in the environment "(?P<env>[^"]*)"'
))
def step_wait_until_see_text_in_env_default(page, text: str, env: str):
    step_wait_until_see_text_in_environment(page, str(DEFAULT_TIMEOUT), text, env)


@when(parsers.re(r'I add the "(?P<channel>[^"]*)" channel to sources'))
def step_add_channel_to_sources(page, channel: str):
    container = page.locator(f"xpath=//mark[text()='{channel}']/../../..")
    container.locator("input[type='checkbox']").check()


@when(parsers.re(
    r'I click the "(?P<name>[^"]*)" item (?P<action>.*?) button'
))
def step_click_item_action_button(page, name: str, action: str):
    if "details" in action:
        icon_class = "fa-list"
    elif "edit" in action:
        icon_class = "fa-edit"
    elif "delete" in action:
        icon_class = "fa-trash"
    else:
        raise ValueError(f"Unknown element with description '{action}'")

    td_element = page.locator(f"xpath=//td[contains(text(), '{name}')]").first
    assert td_element.count(), f"Item '{name}' not found"
    button_xpath = (
        f"./ancestor::tr/td/button/i[contains(@class, '{icon_class}')] | "
        f"./ancestor::tr/td/div/button/i[contains(@class, '{icon_class}')]"
    )
    td_element.locator(f"xpath={button_xpath}").click()


@when(parsers.re(
    r'I click the "(?P<name>[^"]*)" item (?P<action>.*?) button if exists'
))
def step_click_item_action_button_if_exists(page, name: str, action: str):
    if "details" in action:
        icon_class = "fa-list"
    elif "edit" in action:
        icon_class = "fa-edit"
    elif "delete" in action:
        icon_class = "fa-trash"
    else:
        raise ValueError(f"Unknown element with description '{action}'")

    td_locator = page.locator(f"xpath=//td[contains(text(), '{name}')]").first
    if not td_locator.count():
        return
    try:
        button_xpath = (
            f"./ancestor::tr/td/button/i[contains(@class, '{icon_class}')] | "
            f"./ancestor::tr/td/div/button/i[contains(@class, '{icon_class}')]"
        )
        td_locator.locator(f"xpath={button_xpath}").click()
    except Exception:
        pass  # element not found — ignored


# ---------------------------------------------------------------------------
# SSH authorized_keys management
# ---------------------------------------------------------------------------

@when(parsers.re(r'I backup the SSH authorized_keys file of host "(?P<host>[^"]*)"'))
def step_backup_ssh_authorized_keys(host: str):
    auth_keys_path = "/root/.ssh/authorized_keys"
    auth_keys_sav_path = "/root/.ssh/authorized_keys.sav"
    target = get_target(host)
    _out, ret_code = target.run(f"cp {auth_keys_path} {auth_keys_sav_path}")
    assert ret_code == 0, "error backing up authorized_keys on host"


@when(parsers.re(r'I add pre-generated SSH public key to authorized_keys of host "(?P<host>[^"]*)"'))
def step_add_ssh_public_key(host: str):
    from support.file_management import file_inject
    key_filename = "id_rsa_bootstrap-passphrase_linux.pub"
    target = get_target(host)
    source = os.path.join(
        os.path.dirname(__file__), f"../features/upload_files/ssh_keypair/{key_filename}"
    )
    ret_code = file_inject(target, source, f"/tmp/{key_filename}")
    target.run(f"cat /tmp/{key_filename} >> /root/.ssh/authorized_keys", timeout=500)
    assert ret_code, "Error copying ssh pubkey to host"


@when(parsers.re(r'I restore the SSH authorized_keys file of host "(?P<host>[^"]*)"'))
def step_restore_ssh_authorized_keys(host: str):
    auth_keys_path = "/root/.ssh/authorized_keys"
    auth_keys_sav_path = "/root/.ssh/authorized_keys.sav"
    target = get_target(host)
    target.run(f"cp {auth_keys_sav_path} {auth_keys_path}")
    target.run(f"rm {auth_keys_sav_path}")


# ---------------------------------------------------------------------------
# Calendar file
# ---------------------------------------------------------------------------

@when(parsers.re(r'I add "(?P<file>[^"]*)" calendar file as url'))
def step_add_calendar_file_as_url(page, file: str):
    from support.file_management import file_inject
    source = os.path.join(os.path.dirname(__file__), f"../features/upload_files/{file}")
    dest = f"/srv/www/htdocs/pub/{file}"
    server = get_target("server")
    success = file_inject(server, source, dest)
    assert success, "File injection failed"
    server.run(f"chmod 644 {dest}")
    url = f"https://{server.full_hostname}/pub/{file}"
    page.locator("[name='calendar-data-text'], #calendar-data-text").first.fill(url)


# ---------------------------------------------------------------------------
# Ansible playbooks and inventory
# ---------------------------------------------------------------------------

@when(parsers.re(r'I deploy testing playbooks and inventory files to "(?P<host>[^"]*)"'))
def step_deploy_testing_playbooks(host: str):
    from support.file_management import file_inject
    target = get_target(host)
    base = os.path.join(os.path.dirname(__file__), "../features/upload_files/ansible/playbooks")

    dest_orion = "/srv/playbooks/orion_dummy/"
    target.run(f"mkdir -p {dest_orion}")

    files_to_inject = [
        (f"{base}/orion_dummy/playbook_orion_dummy.yml", f"{dest_orion}playbook_orion_dummy.yml"),
        (f"{base}/orion_dummy/hosts", f"{dest_orion}hosts"),
        (f"{base}/orion_dummy/file.txt", f"{dest_orion}file.txt"),
        (f"{base}/playbook_ping.yml", "/srv/playbooks/playbook_ping.yml"),
        (f"{base}/basic_tests.yml", "/srv/playbooks/basic_tests.yml"),
    ]
    for source, dest in files_to_inject:
        success = file_inject(target, source, dest)
        assert success, f'File "{source}" injection failed'

    dest_host_files = "/srv/playbooks/host_files/"
    target.run(f"mkdir -p {dest_host_files}")
    source = f"{base}/host_files/ansible_param_tester.sh"
    success = file_inject(target, source, f"{dest_host_files}ansible_param_tester.sh")
    assert success, f'File "{source}" injection failed'


# ---------------------------------------------------------------------------
# Reactivation key
# ---------------------------------------------------------------------------

@when(parsers.re(r'I enter the reactivation key of "(?P<host>[^"]*)"'))
def step_enter_reactivation_key(page, api_test, host: str):
    system_name = get_system_name(host)
    node_id = api_test.system.retrieve_server_id(system_name)
    react_key = api_test.system.obtain_reactivation_key(node_id)
    page.locator("[name='reactivationKey'], #reactivationKey").first.fill(react_key)
