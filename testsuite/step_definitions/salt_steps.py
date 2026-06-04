# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/salt_steps.rb.

Covers all Salt / bootstrapping steps: Salt master reachability, key
management, service control, pillar data, formulas, salt-ssh, package
states, and minion cleanup.
"""

import re
import time
import os

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target
from support.commonlib import repeat_until_timeout, rh_host, deb_host, transactional_system
from support.env import DEFAULT_TIMEOUT, USE_SALT_BUNDLE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_system_name(host: str) -> str:
    """Return the full hostname for a logical host name."""
    try:
        node = get_target(host)
        return node.full_hostname
    except (NotImplementedError, KeyError):
        return host


def _salt_call_bin() -> str:
    return "venv-salt-call" if USE_SALT_BUNDLE else "salt-call"


def _salt_minion_pkg() -> str:
    return "venv-salt-minion" if USE_SALT_BUNDLE else "salt-minion"


def _pillar_get(key: str, minion: str) -> str:
    """Run salt-call pillar.get on the minion, return raw output."""
    node = get_target(minion)
    salt_call = _salt_call_bin()
    output, _code = node.run(f"{salt_call} pillar.get {key}")
    return output


def _salt_master_pillar_get(key: str) -> str:
    """Run salt pillar.get from the master for sle_minion, return value line."""
    server = get_target("server")
    minion_hostname = get_target("sle_minion").full_hostname
    output, _code = server.run(
        f"salt '{minion_hostname}' pillar.get {key}", check_errors=False
    )
    lines = output.strip().split("\n")
    # The second line (index 1) is the value; if only 1 line, value is empty
    if len(lines) > 1:
        return lines[1].strip()
    return ""


# ---------------------------------------------------------------------------
# Salt master reachability
# ---------------------------------------------------------------------------

@given(parsers.re(r'the Salt master can reach "(?P<minion>[^"]*)"'))
def step_salt_master_can_reach(minion: str):
    system_name = _get_system_name(minion)
    server = get_target("server")

    def _ping():
        out, _code = server.run(f"salt {system_name} test.ping", check_errors=False)
        if system_name in out and "True" in out:
            return True
        return None

    repeat_until_timeout(
        _ping,
        timeout=700,
        message=f"Master cannot communicate with {minion}",
        report_result=True,
    )


# ---------------------------------------------------------------------------
# Remote file / output
# ---------------------------------------------------------------------------

@when(parsers.re(r'I get the contents of the remote file "(?P<filename>[^"]*)"'))
def step_get_remote_file_contents(scenario_state, filename: str):
    output, _code = get_target("server").run(f"cat {filename}")
    scenario_state["output"] = output


# ---------------------------------------------------------------------------
# Salt-minion service control
# ---------------------------------------------------------------------------

@when(parsers.re(r'I stop salt-minion on "(?P<minion>[^"]*)"'))
def step_stop_salt_minion(minion: str):
    node = get_target(minion)
    pkgname = _salt_minion_pkg()
    os_version = node.os_version
    os_family = node.os_family
    if os_family.startswith("sles") and os_version.startswith("11"):
        node.run(f"rc{pkgname} stop", check_errors=False)
    else:
        node.run(f"systemctl stop {pkgname}", check_errors=False)


@when(parsers.re(r'I start salt-minion on "(?P<minion>[^"]*)"'))
def step_start_salt_minion(minion: str):
    node = get_target(minion)
    pkgname = _salt_minion_pkg()
    os_version = node.os_version
    os_family = node.os_family
    if os_family.startswith("sles") and os_version.startswith("11"):
        node.run(f"rc{pkgname} start", check_errors=False)
    else:
        node.run(f"systemctl start {pkgname}", check_errors=False)


@when(parsers.re(r'I restart salt-minion on "(?P<minion>[^"]*)"'))
def step_restart_salt_minion(minion: str):
    node = get_target(minion)
    pkgname = _salt_minion_pkg()
    os_version = node.os_version
    os_family = node.os_family
    if os_family.startswith("sles") and os_version.startswith("11"):
        node.run(f"rc{pkgname} restart", check_errors=False)
    else:
        node.run(f"systemctl restart {pkgname}", check_errors=False)


@when(parsers.re(r'I refresh salt-minion grains on "(?P<minion>[^"]*)"'))
def step_refresh_salt_minion_grains(minion: str):
    node = get_target(minion)
    salt_call = _salt_call_bin()
    node.run(f"{salt_call} saltutil.refresh_grains")


# ---------------------------------------------------------------------------
# Git pillar
# ---------------------------------------------------------------------------

@when("I setup a git_pillar environment on the Salt master")
def step_setup_git_pillar(request):
    from support.file_management import file_inject
    file = "salt_git_pillar_setup.sh"
    source = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../features/upload_files", file)
    )
    dest = f"/tmp/{file}"
    success = file_inject(get_target("server"), source, dest)
    assert success, "File injection failed"
    get_target("server").run(f"sh /tmp/{file} setup", check_errors=True)


@when("I clean up the git_pillar environment on the Salt master")
def step_cleanup_git_pillar():
    from support.file_management import file_inject
    file = "salt_git_pillar_setup.sh"
    source = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../features/upload_files", file)
    )
    dest = f"/tmp/{file}"
    success = file_inject(get_target("server"), source, dest)
    assert success, "File injection failed"
    get_target("server").run(f"sh /tmp/{file} clean", check_errors=True)


# ---------------------------------------------------------------------------
# Salt key management
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I wait at most (?P<key_timeout>\d+) seconds until Salt master sees "(?P<minion>[^"]*)" as "(?P<key_type>[^"]*)"'
))
def step_wait_salt_master_sees_minion(key_timeout: str, minion: str, key_type: str):
    cmd = f"salt-key --list {key_type}"

    def _check():
        system_name = _get_system_name(minion)
        if not system_name:
            return None
        output, code = get_target("server").run(cmd, check_errors=False)
        if code == 0 and system_name in output:
            return True
        return None

    repeat_until_timeout(
        _check,
        timeout=int(key_timeout),
        message=f"Minion '{minion}' not listed among {key_type} keys",
    )


@when(parsers.re(r'I wait until Salt client is inactive on "(?P<minion>[^"]*)"'))
def step_wait_salt_client_inactive(minion: str):
    salt_minion = _salt_minion_pkg()
    # Delegate to the service-inactivity step by using the node directly
    node = get_target(minion)

    def _check():
        out, code = node.run(
            f"systemctl is-active {salt_minion}", check_errors=False
        )
        if code != 0 or "inactive" in out or "failed" in out:
            return True
        return None

    repeat_until_timeout(_check, message=f"Salt client still active on {minion}")


@when(parsers.re(r'I wait until Salt master can reach "(?P<minion>[^"]*)"'))
def step_wait_until_salt_master_can_reach(minion: str):
    system_name = _get_system_name(minion)
    get_target("server").run_until_ok(
        f"bash -c 'until timeout 5s salt {system_name} test.ping; do :; done'"
    )


@when(parsers.re(r'I wait until no Salt job is running on "(?P<minion>[^"]*)"'))
def step_wait_no_salt_job(minion: str):
    target = get_target(minion)
    salt_call = _salt_call_bin()

    def _check():
        output, _code = target.run(
            f"{salt_call} -lquiet saltutil.running", check_errors=False
        )
        if output.strip() == "local:":
            return True
        return None

    repeat_until_timeout(_check, timeout=600, message=f"A Salt job is still running on {minion}")


@when(parsers.re(r'I delete "(?P<host>[^"]*)" key in the Salt master'))
def step_delete_key_salt_master(scenario_state, host: str):
    system_name = _get_system_name(host)
    output, _code = get_target("server").run(
        f"salt-key -y -d {system_name}", check_errors=False
    )
    scenario_state["output"] = output


@when(parsers.re(r'I accept "(?P<host>[^"]*)" key in the Salt master'))
def step_accept_key_salt_master(host: str):
    system_name = _get_system_name(host)
    get_target("server").run(f"salt-key -y --accept={system_name}*")


@when("I list all Salt keys shown on the Salt master")
def step_list_all_salt_keys():
    get_target("server").run("salt-key --list-all", check_errors=False)


# ---------------------------------------------------------------------------
# Grains and OS information
# ---------------------------------------------------------------------------

@when(parsers.re(r'I get OS information of "(?P<host>[^"]*)" from the Master'))
def step_get_os_information(scenario_state, host: str):
    system_name = _get_system_name(host)
    output, _code = get_target("server").run(
        f"salt {system_name} grains.get osfullname"
    )
    scenario_state["output"] = output


@then(parsers.re(r'it should contain a "(?P<content>[^"]*?)" text'))
def step_output_contains_text(scenario_state, content: str):
    output = scenario_state.get("output", "")
    assert re.search(content, output), (
        f"Text '{content}' not found in output:\n{output}"
    )


@then(parsers.re(r'it should contain the OS of "(?P<host>[^"]*)"'))
def step_output_contains_os(scenario_state, host: str):
    node = get_target(host)
    os_family = node.os_family
    family = r"(Leap|Tumbleweed)" if os_family.startswith("opensuse") else "SLES"
    output = scenario_state.get("output", "")
    assert re.search(family, output), (
        f"OS pattern '{family}' not found in output:\n{output}"
    )


# ---------------------------------------------------------------------------
# State apply
# ---------------------------------------------------------------------------

@when(parsers.re(r'I apply state "(?P<state>[^"]*)" to "(?P<host>[^"]*)"'))
def step_apply_state(state: str, host: str):
    system_name = _get_system_name(host)
    get_target("server").run(f"salt {system_name} state.apply {state}")


# ---------------------------------------------------------------------------
# Port checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'salt-api should be listening on local port (?P<port>\d+)'))
def step_salt_api_listening(scenario_state, port: str):
    output, _code = get_target("server").run(f"ss -ntl | grep {port}")
    scenario_state["output"] = output
    assert re.search(rf"127\.0\.0\.1:{port}", output), (
        f"salt-api not listening on local port {port}: {output}"
    )


@then(parsers.re(r'salt-master should be listening on public port (?P<port>\d+)'))
def step_salt_master_listening(scenario_state, port: str):
    output, _code = get_target("server").run(f"ss -ntl | grep {port}")
    scenario_state["output"] = output
    assert re.search(rf"(0\.0\.0\.0|\*|\[::\]):{port}", output), (
        f"salt-master not listening on public port {port}: {output}"
    )


# ---------------------------------------------------------------------------
# Registration checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'"(?P<host>.*?)" should not be registered'))
def step_should_not_be_registered(api_test, host: str):
    system_name = _get_system_name(host)
    names = [s["name"] for s in api_test.system.list_systems()]
    assert system_name not in names, f"'{host}' should not be registered but is"


@then(parsers.re(r'"(?P<host>.*?)" should be registered'))
def step_should_be_registered(api_test, host: str):
    system_name = _get_system_name(host)
    names = [s["name"] for s in api_test.system.list_systems()]
    assert system_name in names, f"'{host}' is not registered"


@then(parsers.re(r'"(?P<host>.*?)" should have been reformatted'))
def step_should_have_been_reformatted(host: str):
    system_name = _get_system_name(host)
    output, _code = get_target("server").run(
        f"salt {system_name} file.file_exists /intact"
    )
    assert "False" in output, f"Minion {host} is intact (expected /intact to be absent)"


# ---------------------------------------------------------------------------
# UI-related Salt steps (browser + Capybara-style, using Playwright page)
# ---------------------------------------------------------------------------

@when("I click on preview")
def step_click_on_preview(page):
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        stop_btn = page.query_selector("button#stop")
        if stop_btn and stop_btn.is_visible():
            print("Stop button visible, search ongoing.")
        else:
            page.click("button#preview")
        run_visible = page.wait_for_selector(
            "button#run", state="visible", timeout=5000
        )
        if run_visible:
            break
        print(f"Run button not visible after clicking preview (attempt {attempt}).")
    run_btn = page.query_selector("button#run")
    assert run_btn and run_btn.is_visible(), (
        f"Preview button not working: run button not visible after {max_attempts} attempts."
    )


@when("I click on stop waiting")
def step_click_stop_waiting(page):
    page.click("button#stop")


@when("I click on run")
def step_click_on_run(page):
    page.wait_for_selector("button#run", state="visible",
                           timeout=DEFAULT_TIMEOUT * 1000)
    page.click("button#run")


@when(parsers.re(r'I expand the results for "(?P<host>[^"]*)"'))
def step_expand_results(page, host: str):
    system_name = _get_system_name(host)
    page.click(f"div[id='{system_name}']")


@when(parsers.re(r'I enter command "(?P<cmd>[^"]*)"'))
def step_enter_command(page, cmd: str):
    page.fill("input[name='command']", cmd)


@when(parsers.re(r'I enter target "(?P<host>[^"]*)"'))
def step_enter_target(page, host: str):
    value = _get_system_name(host)
    page.fill("input[name='target']", value)


@then(parsers.re(
    r'I should see "(?P<text>[^"]*)" in the command output for "(?P<host>[^"]*)"'
))
def step_see_text_in_command_output(page, text: str, host: str):
    system_name = _get_system_name(host)
    locator = page.locator(f"pre[id='{system_name}-results']")
    content = locator.text_content()
    assert text in content, (
        f"Text '{text}' not found in results for {system_name}:\n{content}"
    )


# ---------------------------------------------------------------------------
# Salt formulas (UI)
# ---------------------------------------------------------------------------

@when(parsers.re(r'I manually install the "(?P<package>[^"]*)" formula on the server'))
def step_install_formula(package: str):
    get_target("server").run("zypper --non-interactive refresh")
    get_target("server").run(
        f"zypper --non-interactive install --force {package}-formula"
    )


@when(parsers.re(r'I manually uninstall the "(?P<package>[^"]*)" formula from the server'))
def step_uninstall_formula(package: str):
    get_target("server").run(
        f"zypper --non-interactive remove {package}-formula"
    )
    if package == "uyuni-config":
        get_target("server").run(
            f"zypper --non-interactive remove {package}-modules"
        )


@when(parsers.re(r'I synchronize all Salt dynamic modules on "(?P<host>[^"]*)"'))
def step_sync_salt_modules(host: str):
    system_name = _get_system_name(host)
    get_target("server").run(f"salt {system_name} saltutil.sync_all")


@when(parsers.re(r'I remove "(?P<filename>[^"]*)" from salt cache on "(?P<host>[^"]*)"'))
def step_remove_from_salt_cache(filename: str, host: str):
    from support.file_management import file_delete
    node = get_target(host)
    salt_cache = (
        "/var/cache/venv-salt-minion/" if USE_SALT_BUNDLE else "/var/cache/salt/"
    )
    file_delete(node, f"{salt_cache}{filename}")


@when(parsers.re(
    r'I remove "(?P<filename>[^"]*)" from salt minion config directory on "(?P<host>[^"]*)"'
))
def step_remove_from_salt_minion_config(filename: str, host: str):
    from support.file_management import file_delete
    node = get_target(host)
    salt_config = (
        "/etc/venv-salt-minion/minion.d/" if USE_SALT_BUNDLE else "/etc/salt/minion.d/"
    )
    file_delete(node, f"{salt_config}{filename}")


@when(parsers.re(r'I configure salt minion on "(?P<host>[^"]*)"'))
def step_configure_salt_minion(host: str):
    server_hostname = get_target("server").full_hostname
    content = (
        f"\nmaster: {server_hostname}\n"
        "server_id_use_crc: adler32\n"
        "enable_legacy_startup_events: False\n"
        "enable_fqdns_grains: False\n"
        "start_event_grains:\n"
        "  - machine_id\n"
        "  - saltboot_initrd\n"
        "  - susemanager"
    )
    salt_config = (
        "/etc/venv-salt-minion/minion.d/" if USE_SALT_BUNDLE else "/etc/salt/minion.d/"
    )
    node = get_target(host)
    node.run(f"echo '{content}' > {salt_config}susemanager.conf")


@when(parsers.re(
    r'I store "(?P<content>[^"]*)" into file "(?P<filename>[^"]*)" '
    r'in salt minion config directory on "(?P<host>[^"]*)"'
))
def step_store_in_salt_minion_config_dir(content: str, filename: str, host: str):
    salt_config = (
        "/etc/venv-salt-minion/minion.d/" if USE_SALT_BUNDLE else "/etc/salt/minion.d/"
    )
    node = get_target(host)
    node.run(f"echo '{content}' > {salt_config}{filename}")


@when(parsers.re(r'I (?P<action>[^ ]*) the "(?P<formula>[^"]*)" formula'))
def step_toggle_formula(page, action: str, formula: str):
    # Wait for chooseFormulas to be present and access its innerHTML to refresh DOM
    page.wait_for_selector("#chooseFormulas")
    page.eval_on_selector("#chooseFormulas", "el => el.innerHTML")

    if action == "check":
        unchecked_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-square-o']"
        if page.locator(f"xpath={unchecked_xpath}").count() > 0:
            page.locator(f"xpath={unchecked_xpath}").click()
        # else already checked — verify
    elif action == "uncheck":
        checked_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-check-square-o']"
        if page.locator(f"xpath={checked_xpath}").count() > 0:
            page.locator(f"xpath={checked_xpath}").click()


@then(parsers.re(r'the "(?P<formula>[^"]*)" formula should be (?P<state>[^ ]*)'))
def step_formula_state(page, formula: str, state: str):
    page.eval_on_selector("#chooseFormulas", "el => el.innerHTML")
    if state == "checked":
        wrong_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-square-o']"
        right_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-check-square-o']"
    else:  # unchecked
        wrong_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-check-square-o']"
        right_xpath = f"//button[@id = '{formula}']/i[@class = 'fa fa-lg fa-square-o']"

    assert page.locator(f"xpath={wrong_xpath}").count() == 0, (
        f"Checkbox for '{formula}' is not {state}"
    )
    assert page.locator(f"xpath={right_xpath}").count() > 0, (
        f"Checkbox for '{formula}' could not be found in state {state}"
    )


# ---------------------------------------------------------------------------
# Package list UI
# ---------------------------------------------------------------------------

@when(parsers.re(r'I list packages with "(?P<str>[^"]*)"'))
def step_list_packages_with(page, str: str):
    page.fill("input#package-search", str)

    def _search_enabled():
        btn = page.query_selector("button#search")
        return btn and not btn.is_disabled()

    repeat_until_timeout(
        _search_enabled, timeout=60, message="Search button not enabled"
    )
    page.click("button#search")


@when(parsers.re(
    r'I change the state of "(?P<pkg>[^"]*)" to "(?P<state>[^"]*)" and "(?P<instd_state>[^"]*)"'
))
def step_change_package_state(page, pkg: str, state: str, instd_state: str):
    page.select_option(f"#{pkg}-pkg-state", label=state)
    if instd_state and state == "Installed":
        page.select_option(f"#{pkg}-version-constraint", label=instd_state)


@when("I click apply")
def step_click_apply(page):
    page.click("button#apply")


@when("I click save")
def step_click_save(page):
    page.click("button#save")


# ---------------------------------------------------------------------------
# Timezone / keymap / language checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'the timezone on "(?P<minion>[^"]*)" should be "(?P<timezone>[^"]*)"'))
def step_timezone_check(minion: str, timezone: str):
    node = get_target(minion)
    output, _code = node.run("date +%Z")
    result = output.strip()
    if result == "CEST":
        result = "CET"
    assert result == timezone, f"Timezone {timezone} != {result}"


@then(parsers.re(r'the keymap on "(?P<minion>[^"]*)" should be "(?P<keymap>[^"]*)"'))
def step_keymap_check(minion: str, keymap: str):
    node = get_target(minion)
    output, _code = node.run("grep 'KEYMAP=' /etc/vconsole.conf")
    assert output.strip() == f"KEYMAP={keymap}", (
        f"Keymap '{keymap}' != '{output.strip()}'"
    )


@then(parsers.re(r'the language on "(?P<minion>[^"]*)" should be "(?P<language>[^"]*)"'))
def step_language_check(minion: str, language: str):
    node = get_target(minion)
    output, _code = node.run("grep 'RC_LANG=' /etc/sysconfig/language", check_errors=False)
    if output.strip() == f'RC_LANG="{language}"':
        return
    output2, _code2 = node.run("grep 'LANG=' /etc/locale.conf", check_errors=False)
    assert output2.strip() == f"LANG={language}", (
        f"Language '{language}' not found: RC_LANG output='{output.strip()}', "
        f"LANG output='{output2.strip()}'"
    )


# ---------------------------------------------------------------------------
# Pillar
# ---------------------------------------------------------------------------

@when("I refresh the pillar data")
def step_refresh_pillar_data():
    minion_hostname = get_target("sle_minion").full_hostname
    get_target("server").run(
        f"salt '{minion_hostname}' saltutil.refresh_pillar wait=True"
    )


@when("I wait until there is no pillar refresh salt job active")
def step_wait_no_pillar_refresh_job():
    def _check():
        output, _ = get_target("server").run("salt-run jobs.active")
        return True if "saltutil.refresh_pillar" not in output else None

    repeat_until_timeout(_check, message="pillar refresh job still active")


@when(parsers.re(
    r'I wait until there is no Salt job calling the module "(?P<salt_module>[^"]*)" on "(?P<minion>[^"]*)"'
))
def step_wait_no_salt_job_module(salt_module: str, minion: str):
    target = get_target(minion)
    salt_call = _salt_call_bin()

    def _check():
        out, code = target.run(
            f"{salt_call} -lquiet saltutil.running | grep {salt_module}",
            check_errors=False,
        )
        return True if code != 0 else None

    repeat_until_timeout(_check, timeout=600,
                         message=f"Salt job '{salt_module}' still running on {minion}")


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should be "(?P<value>[^"]*)" on "(?P<minion>[^"]*)"'
))
def step_pillar_data_equals(key: str, value: str, minion: str):
    output = _pillar_get(key, minion)
    if value == "":
        assert len(output.split("\n")) == 1, (
            f"Output has more than one line: {output}"
        )
    else:
        lines = output.split("\n")
        assert len(lines) > 1, f"Output value not found: {output}"
        assert lines[1].strip() == value, (
            f"Output value is different from '{value}': {output}"
        )


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should contain "(?P<value>[^"]*)" on "(?P<minion>[^"]*)"'
))
def step_pillar_data_contains(key: str, value: str, minion: str):
    output = _pillar_get(key, minion)
    assert value in output, f"Output doesn't contain '{value}': {output}"


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should not contain "(?P<value>[^"]*)" on "(?P<minion>[^"]*)"'
))
def step_pillar_data_not_contains(key: str, value: str, minion: str):
    output = _pillar_get(key, minion)
    assert value not in output, f"Output contains '{value}': {output}"


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should be empty on "(?P<minion>[^"]*)"'
))
def step_pillar_data_empty(key: str, minion: str):
    output = ""

    def _check():
        nonlocal output
        output = _pillar_get(key, minion)
        return True if len(output.split("\n")) == 1 else None

    repeat_until_timeout(
        _check,
        timeout=DEFAULT_TIMEOUT,
        message=f"Output has more than one line: {output}",
        report_result=True,
    )


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should be empty on the Salt master'
))
def step_pillar_data_empty_on_master(key: str):
    output = _salt_master_pillar_get(key)
    assert output == "", f"Output value is not empty: {output}"


@then(parsers.re(
    r'the pillar data for "(?P<key>[^"]*)" should be "(?P<value>[^"]*)" on the Salt master'
))
def step_pillar_data_equals_on_master(key: str, value: str):
    output = _salt_master_pillar_get(key)
    assert output.strip() == value, (
        f"Output value is different from '{value}': {output}"
    )


# ---------------------------------------------------------------------------
# Download / token steps
# ---------------------------------------------------------------------------

@given(parsers.re(
    r'I try to download "(?P<rpm>[^"]*)" from channel "(?P<channel>[^"]*)"'
))
def step_try_to_download(scenario_state, rpm: str, channel: str):
    import urllib.request
    import urllib.error
    import ssl
    server_host = get_target("server").full_hostname
    token = scenario_state.get("token")
    url = f"https://{server_host}/rhn/manager/download/{channel}/getPackage/{rpm}"
    if token:
        url = f"{url}?{token}"

    scenario_state["download_path"] = None
    scenario_state["download_error"] = None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=rpm, delete=False) as tmpfile:
        scenario_state["download_path"] = tmpfile.name
        try:
            with urllib.request.urlopen(url, context=ctx) as resp:
                tmpfile.write(resp.read())
        except urllib.error.HTTPError as e:
            scenario_state["download_error"] = e


@then(parsers.re(r'the download should get a (?P<code>\d+) response'))
def step_download_response_code(scenario_state, code: str):
    error = scenario_state.get("download_error")
    assert error is not None, "Expected an HTTP error but got none"
    assert error.code == int(code), (
        f"Expected HTTP {code}, got {error.code}"
    )


@then("the download should get no error")
def step_download_no_error(scenario_state):
    error = scenario_state.get("download_error")
    assert error is None, f"Expected no download error, got: {error}"


# ---------------------------------------------------------------------------
# Key UI steps (Salt Onboarding UI)
# ---------------------------------------------------------------------------

@when(parsers.re(r'I reject "(?P<host>[^"]*)" from the Pending section'))
def step_reject_from_pending(page, host: str):
    system_name = _get_system_name(host)
    xpath = f"//tr[td[contains(.,'{system_name}')]]//button[@aria-label = 'Reject']"
    page.click(f"xpath={xpath}")


@when(parsers.re(r'I delete "(?P<host>[^"]*)" from the Rejected section'))
def step_delete_from_rejected(page, host: str):
    system_name = _get_system_name(host)
    xpath = f"//tr[td[contains(.,'{system_name}')]]//button[@aria-label = 'Delete']"
    page.click(f"xpath={xpath}")


@when(parsers.re(r'I see "(?P<host>[^"]*)" fingerprint'))
def step_see_fingerprint(page, host: str):
    node = get_target(host)
    salt_call = _salt_call_bin()
    output, _code = node.run(f"{salt_call} --local key.finger")
    lines = output.split("\n")
    fing = lines[1].strip() if len(lines) > 1 else None
    assert fing, "Fingerprint line not found in salt-call output"
    content = page.content()
    assert fing in content, f"Fingerprint '{fing}' not found on page"


@when(parsers.re(r'I accept "(?P<host>[^"]*)" key'))
def step_accept_key_ui(page, host: str):
    system_name = _get_system_name(host)
    xpath = f"//tr[td[contains(.,'{system_name}')]]//button[@aria-label = 'Accept']"
    page.click(f"xpath={xpath}")


@when(parsers.re(r'I refresh page until I see "(?P<minion>[^"]*?)" hostname as text'))
def step_refresh_until_see_hostname(page, minion: str):
    system_name = _get_system_name(minion)

    def _check():
        page.reload()
        content = page.locator("#spacewalk-content").text_content()
        return True if system_name in content else None

    repeat_until_timeout(_check, message=f"Hostname {system_name} not visible")


@when(parsers.re(r'I refresh page until I do not see "(?P<minion>[^"]*?)" hostname as text'))
def step_refresh_until_not_see_hostname(page, minion: str):
    system_name = _get_system_name(minion)

    def _check():
        page.reload()
        content = page.locator("#spacewalk-content").text_content()
        return True if system_name not in content else None

    repeat_until_timeout(_check, message=f"Hostname {system_name} still visible")


# ---------------------------------------------------------------------------
# Salt event log
# ---------------------------------------------------------------------------

@then("the salt event log on server should contain no failures")
def step_salt_event_log_no_failures():
    from support.file_management import file_inject
    file = "salt_event_parser.py"
    source = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../features/upload_files", file)
    )
    dest = f"/tmp/{file}"
    success = file_inject(get_target("server"), source, dest)
    assert success, "File injection failed"

    output, _code = get_target("server").run(f"python3 /tmp/{file}")
    blocks = re.split(r"(?=# Failure \d+)", output)
    filtered = [b for b in blocks if "remove lock to allow installation of hoag-dummy" not in b]
    count_failures = filtered.__str__().count("false")
    assert count_failures == 0, (
        f"\nFound {count_failures} failures in salt event log:\n{''.join(filtered)}\n"
    )


# ---------------------------------------------------------------------------
# Salt package installation
# ---------------------------------------------------------------------------

@when(parsers.re(r'I install Salt packages from "(?P<host>[^"]*)"'))
def step_install_salt_packages(host: str):
    target = get_target(host)
    pkgs = "venv-salt-minion" if USE_SALT_BUNDLE else "salt salt-minion"
    os_family = target.os_family

    if os_family.startswith("suse") or os_family.startswith("sles") or os_family.startswith("opensuse"):
        target.run(f"test -e /usr/bin/zypper && zypper --non-interactive install -y {pkgs}",
                   check_errors=False)
    elif "transactional" in (getattr(target, "os_type", "") or ""):
        target.run(f"test -e /usr/bin/zypper && transactional-update -n pkg install {pkgs}",
                   check_errors=False)
    elif rh_host(host):
        target.run(f"test -e /usr/bin/yum && yum -y install {pkgs}", check_errors=False)
    elif deb_host(host):
        deb_pkgs = pkgs if USE_SALT_BUNDLE else "salt-common salt-minion"
        target.run(f"test -e /usr/bin/apt && apt -y install {deb_pkgs}", check_errors=False)


@when(parsers.re(
    r'I enable repositories before installing Salt on this "(?P<host>[^"]*)"'
))
def step_enable_repos_before_salt(host: str):
    node = get_target(host)
    node.run(
        'zypper --non-interactive addrepo --no-gpgcheck tools_additional_repo || true',
        check_errors=False,
    )


@when(parsers.re(
    r'I disable repositories after installing Salt on this "(?P<host>[^"]*)"'
))
def step_disable_repos_after_salt(host: str):
    node = get_target(host)
    node.run(
        'zypper --non-interactive removerepo tools_additional_repo || true',
        check_errors=False,
    )


# ---------------------------------------------------------------------------
# Spacecmd event history
# ---------------------------------------------------------------------------

@then(parsers.re(r'I run spacecmd listeventhistory for "(?P<host>[^"]*)"'))
def step_spacecmd_list_event_history(host: str):
    system_name = _get_system_name(host)
    get_target("server").run("spacecmd -u admin -p admin clear_caches")
    get_target("server").run(
        f"spacecmd -u admin -p admin system_listeventhistory {system_name}"
    )


# ---------------------------------------------------------------------------
# Full Salt minion cleanup
# ---------------------------------------------------------------------------

@when(parsers.re(r'I perform a full salt minion cleanup on "(?P<host>[^"]*)"'))
def step_full_salt_minion_cleanup(host: str):
    node = get_target(host)

    salt_bundle_config_dir = "/etc/venv-salt-minion"
    salt_classic_config_dir = "/etc/salt"
    salt_bundle_cleanup_paths = (
        "/var/cache/venv-salt-minion /run/venv-salt-minion "
        "/var/log/venv-salt-minion.log /var/tmp/.root*"
    )
    salt_classic_cleanup_paths = (
        "/var/cache/salt/minion /var/run/salt /run/salt /var/log/salt /var/tmp/.root*"
    )

    # File cleanup within config directories
    for cfg in (salt_bundle_config_dir, salt_classic_config_dir):
        node.run(f"rm -f {cfg}/grains {cfg}/minion_id", check_errors=False)
        node.run(
            f"find {cfg}/minion.d/ -type f ! -name '00-venv.conf' -delete",
            check_errors=False,
        )
        node.run(f"rm -f {cfg}/pki/minion/*", check_errors=False)

    node.run(
        f"rm -Rf /root/salt {salt_bundle_cleanup_paths} {salt_classic_cleanup_paths}",
        check_errors=False,
    )

    # Remove packages
    node.run(
        "zypper --non-interactive remove --clean-deps venv-salt-minion salt salt-minion || true",
        check_errors=False,
    )

    # Disable repos
    for repo in ("tools_update_repo", "tools_pool_repo"):
        node.run(f"zypper --non-interactive removerepo {repo} || true", check_errors=False)


# ---------------------------------------------------------------------------
# Pillar top file installation
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I install a salt pillar top file for "(?P<files>[^"]*)" with target "(?P<host>[^"]*)" on the server'
))
def step_install_pillar_top_file(files: str, host: str):
    from support.file_management import inject_salt_pillar_file, generate_temp_file
    system_name = "*" if host == "*" else _get_system_name(host)
    script = f"base:\n  '{system_name}':\n"
    for f in re.split(r",\s*", files):
        script += f"    - '{f}'\n"
    temp_path = generate_temp_file("top.sls", script)
    inject_salt_pillar_file(temp_path, "top.sls")
    os.unlink(temp_path)


@when("I install the package download endpoint pillar file on the server")
def step_install_pkg_endpoint_pillar(scenario_state):
    import urllib.parse
    endpoint = scenario_state.get("custom_download_endpoint", "")
    parsed = urllib.parse.urlparse(endpoint)
    filepath = "/srv/pillar/pkg_endpoint.sls"
    content = (
        f"pkg_download_point_protocol: {parsed.scheme}\n"
        f"pkg_download_point_host: {parsed.hostname}\n"
        f"pkg_download_point_port: {parsed.port}"
    )
    get_target("server").run(f'echo -e "{content}" > {filepath}')


@when("I delete the package download endpoint pillar file from the server")
def step_delete_pkg_endpoint_pillar():
    from support.file_management import file_delete
    code = file_delete(get_target("server"), "/srv/pillar/pkg_endpoint.sls")
    assert code == 0, "File deletion failed"


# ---------------------------------------------------------------------------
# Custom formula metadata
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I install "(?P<file>[^"]*)" to custom formula metadata directory "(?P<formula>[^"]*)"'
))
def step_install_formula_metadata(file: str, formula: str):
    from support.file_management import file_inject
    source = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../features/upload_files", file)
    )
    dest = f"/srv/formula_metadata/{formula}/{file}"
    get_target("server").run(f"mkdir -p /srv/formula_metadata/{formula}")
    success = file_inject(get_target("server"), source, dest)
    assert success, "File injection failed"
    get_target("server").run(f"chmod 644 {dest}")


# ---------------------------------------------------------------------------
# venv-salt-minion migration
# ---------------------------------------------------------------------------

@when(parsers.re(r'I migrate "(?P<host>[^"]*)" from salt-minion to venv-salt-minion'))
def step_migrate_to_venv_salt_minion(host: str):
    node = get_target(host)
    system_name = node.full_hostname
    migrate = f"salt {system_name} state.apply util.mgr_switch_to_venv_minion"
    get_target("server").run(migrate, check_errors=True)


@when(parsers.re(r'I purge salt-minion on "(?P<host>[^"]*)" after a migration'))
def step_purge_salt_minion_after_migration(host: str):
    node = get_target(host)
    system_name = node.full_hostname
    cleanup = (
        f"salt {system_name} state.apply util.mgr_switch_to_venv_minion "
        "pillar='{\"mgr_purge_non_venv_salt_files\": True, \"mgr_purge_non_venv_salt\": True}'"
    )
    get_target("server").run(cleanup, check_errors=True)


# ---------------------------------------------------------------------------
# Highstate
# ---------------------------------------------------------------------------

@when(parsers.re(r'I apply highstate on "(?P<host>[^"]*)"'))
def step_apply_highstate(host: str):
    system_name = _get_system_name(host)
    if "ssh_minion" in host:
        cmd = "mgr-salt-ssh"
    elif any(k in host for k in ("minion", "build", "proxy")):
        cmd = "salt"
    else:
        cmd = "salt"
    get_target("server").run_until_ok(f"{cmd} {system_name} state.highstate")


# ---------------------------------------------------------------------------
# Field select (formula UI)
# ---------------------------------------------------------------------------

@when(parsers.re(r'I select "(?P<value>[^"]*)" in (?P<box>.*) field'))
def step_select_in_field(page, value: str, box: str):
    from support.constants import FIELD_IDS
    field_id = FIELD_IDS.get(box, box)
    page.select_option(f"#{field_id}", label=value)


# ---------------------------------------------------------------------------
# Base channel set assertion
# ---------------------------------------------------------------------------

@then("the system should have a base channel set")
def step_system_should_have_base_channel(page):
    from support.commonlib import check_text
    assert not check_text(
        page,
        "This system has no Base Software Channel. You can select a Base Channel from the list below.",
        timeout=5,
    ), "System has no base channel set"
