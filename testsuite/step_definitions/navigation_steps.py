# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/navigation_steps.rb.

Covers browser-driven navigation steps needed by the validation slice features:
  - allcli_action_chain.feature
  - sle_minion.feature
"""

import re
import time

from pytest_bdd import given, when, then, parsers

from support.commonlib import (
    check_text,
    wait_for_ajax,
    click_button_and_wait,
    click_link_and_wait,
    refresh_page,
    repeat_until_timeout,
)
from support.embedded_steps.navigation_helper import (
    authorize_user,
    follow_left_menu,
    wait_for_text,
    wait_for_text_refreshing,
    fill_field,
    enter_text_in_field,
    select_option_from_field,
    follow_link_in_content_area,
    click_on,
    wait_for_text_or,
)
from support.navigation_helper import (
    toggle_checkbox,
    checkbox_state,
    toggle_checkbox_in_list,
    toggle_checkbox_in_package_list,
    filter_by_package_name,
)
from support.remote_nodes_env import get_target, get_system_name
from support.env import APP_HOST, DEFAULT_TIMEOUT
from support.constants import PACKAGE_BY_CLIENT, PKGARCH_BY_CLIENT, BASE_CHANNEL_BY_CLIENT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------



def _get_system_id(api_test, host: str) -> int:
    """Return the numeric system ID for a host via the API."""
    node = get_target(host)
    result = api_test.system.search_by_name(node.full_hostname)
    if not result:
        raise KeyError(f"No system found for hostname: {node.full_hostname}")
    return result[0]["id"]


def _toggle_checkbox_in_list(page, text: str, check: bool):
    """Check or uncheck the first checkbox in a table row containing *text*."""
    xpath = f"//table/tbody/tr[.//td[contains(.,'{text}')]]//input[@type='checkbox']"
    row = page.locator(f"xpath={xpath}").first
    row.set_checked(check)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@given(parsers.re(r'I am authorized for the "(?P<section>[^"]*)" section'))
def step_authorized_for_section(page, section: str):
    mapping = {
        "Admin": ("admin", "admin"),
        "Images": ("kiwikiwi", "kiwikiwi"),
        "Docker": ("docker", "docker"),
    }
    user, password = mapping.get(section, ("admin", "admin"))
    authorize_user(page, user, password)


# ---------------------------------------------------------------------------
# System overview page
# ---------------------------------------------------------------------------

@given(parsers.re(r'I am on the Systems overview page of this "(?P<host>[^"]*)"'))
def step_systems_overview_page(page, api_test, host: str):
    system_id = _get_system_id(api_test, host)
    overview_url = f"/rhn/systems/details/Overview.do?sid={system_id}"
    page.goto(f"{APP_HOST}{overview_url}", wait_until="domcontentloaded")
    if not page.url.endswith(overview_url):
        page.goto(f"{APP_HOST}{overview_url}", wait_until="domcontentloaded")
    wait_for_ajax(page)


# ---------------------------------------------------------------------------
# Left menu navigation
# ---------------------------------------------------------------------------

@when(parsers.re(r'I follow the left menu "(?P<menu_path>[^"]*)"'))
@given(parsers.re(r'I follow the left menu "(?P<menu_path>[^"]*)"'))
def step_follow_left_menu(page, menu_path: str):
    follow_left_menu(page, menu_path)


# ---------------------------------------------------------------------------
# Generic link following
# ---------------------------------------------------------------------------

@when(parsers.re(r'I follow "(?P<text>[^"]*)"$'))
@given(parsers.re(r'I follow "(?P<text>[^"]*)"$'))
def step_follow_link(page, text: str):
    click_link_and_wait(page, text)


# ---------------------------------------------------------------------------
# Click on button/link
# ---------------------------------------------------------------------------

@when(parsers.re(r'I click on "(?P<text>[^"]*)"'))
def step_click_on(page, text: str):
    click_on(page, text)


# ---------------------------------------------------------------------------
# Wait for text
# ---------------------------------------------------------------------------

@when(parsers.re(r'I wait until I see "(?P<text>[^"]*)" text$'))
def step_wait_until_see_text(page, text: str):
    wait_for_text(page, text)


@when(parsers.re(r'I wait until I do not see "(?P<text>[^"]*)" text$'))
def step_wait_until_not_see_text(page, text: str):
    def _not_present():
        visible = check_text(page, text, timeout=3)
        return (not visible) or None
    repeat_until_timeout(
        _not_present,
        message=f"Text '{text}' is still visible",
    )


# ---------------------------------------------------------------------------
# Wait for name, refreshing
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I wait until I see the name of "(?P<host>[^"]*)", refreshing the page'
))
def step_wait_until_see_name_refreshing(page, host: str):
    system_name = get_system_name(host)
    has_csv = check_text(page, "Download CSV", timeout=3)
    has_keys = check_text(page, "Keys", timeout=3)
    if not has_csv and not has_keys:
        raise AssertionError("Overview System page didn't load")
    wait_for_text_refreshing(page, system_name)


# ---------------------------------------------------------------------------
# Hostname visibility assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see "(?P<host>[^"]*)" short hostname'))
def step_should_see_short_hostname(page, host: str):
    system_name = get_system_name(host).partition(".")[0]
    assert check_text(page, system_name), (
        f"Short hostname {system_name} is not present"
    )


@then(parsers.re(r'I should see "(?P<host>[^"]*)" hostname'))
def step_should_see_hostname(page, host: str):
    system_name = get_system_name(host)
    assert check_text(page, system_name), f"Hostname {system_name} is not present"


# ---------------------------------------------------------------------------
# Text assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a "(?P<text>[^"]*)" text'))
def step_should_see_text(page, text: str):
    assert check_text(page, text), f"Text '{text}' not found"


# ---------------------------------------------------------------------------
# Field entry
# ---------------------------------------------------------------------------

@when(parsers.re(r'I enter "(?P<value>[^"]*)" as "(?P<field>[^"]*)"'))
def step_enter_as_field(page, value: str, field: str):
    enter_text_in_field(page, value, field)


@when(parsers.re(r'I enter "(?P<value>[^"]*)" as the filtered package name'))
def step_enter_filtered_package_name(page, value: str):
    loc = page.locator("input[placeholder='Filter by Package Name: ']").first
    loc.fill(value)


@when(parsers.re(r'I enter the hostname of "(?P<host>[^"]*)" as "(?P<field>[^"]*)"'))
def step_enter_hostname_as_field(page, host: str, field: str):
    system_name = get_system_name(host)
    enter_text_in_field(page, system_name, field)


# ---------------------------------------------------------------------------
# Select / dropdown
# ---------------------------------------------------------------------------

@when(parsers.re(r'I select "(?P<option>[^"]*)" from "(?P<field>[^"]*)"'))
def step_select_from(page, option: str, field: str):
    select_option_from_field(page, option, field)


@when(parsers.re(
    r'I select the hostname of "(?P<host>[^"]*)" from "(?P<field>[^"]*)"'
    r'(?P<if_present>(?: if present)?)$'
))
def step_select_hostname_from(page, host: str, field: str, if_present: str):
    try:
        system_name = get_system_name(host)
    except (KeyError, NotImplementedError):
        if if_present.strip():
            return
        raise
    select_option_from_field(page, system_name, field)


# ---------------------------------------------------------------------------
# Checkbox
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check the "(?P<host>[^"]*)" client'))
def step_check_client(page, host: str):
    system_name = get_system_name(host)
    _toggle_checkbox_in_list(page, system_name, True)


@when(parsers.re(r'I check "(?P<text>[^"]*)" in the list'))
def step_check_in_list(page, text: str):
    _toggle_checkbox_in_list(page, text, True)


# ---------------------------------------------------------------------------
# Radio button
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check radio button "(?P<radio>[^"]*)"'))
@given(parsers.re(r'I check radio button "(?P<radio>[^"]*)"'))
def step_check_radio_button(page, radio: str):
    loc = page.get_by_label(radio).first
    if not loc.is_checked():
        loc.check()


# ---------------------------------------------------------------------------
# Filter button
# ---------------------------------------------------------------------------

@when("I click on the filter button")
def step_click_filter_button(page):
    page.locator("button.spacewalk-button-filter").click()
    assert check_text(page, "is filtered", timeout=20), (
        "Filter was not applied: 'is filtered' text did not appear"
    )


@then(parsers.re(
    r'I click on the filter button until page does contain "(?P<text>[^"]*)" text'
))
def step_click_filter_until_contains(page, text: str):
    def _attempt():
        if check_text(page, text, timeout=3):
            return True
        try:
            page.locator("button.spacewalk-button-filter").click()
            check_text(page, "is filtered", timeout=3)
        except Exception:
            pass
        return None

    repeat_until_timeout(
        _attempt,
        message=f"'{text}' was not found after clicking filter",
    )


# ---------------------------------------------------------------------------
# Clear SSM button
# ---------------------------------------------------------------------------

@when("I click on the clear SSM button")
def step_click_clear_ssm(page):
    page.locator("xpath=//*[@id='clear-ssm']").click()


# ---------------------------------------------------------------------------
# Table FINISHED check
# ---------------------------------------------------------------------------

@when(
    "I wait until the table contains "
    '"FINISHED" or "SKIPPED" followed by "FINISHED" in its first rows'
)
def step_wait_table_finished(page):
    repeat_until_timeout(
        lambda: _check_table_finished(page),
        timeout=800,
        message="Task does not look FINISHED yet",
    )


def _check_table_finished(page):
    """Check for FINISHED/SKIPPED status in the first 10 rows of the task table."""
    page.reload()
    wait_for_ajax(page)

    base_table = (
        "//table[.//th[contains(*/text(), 'Status')] "
        "and .//th[contains(*/text(), 'Start Time')]]"
    )
    status_col = f"{base_table}//th[contains(*/text(), 'Status')]/preceding-sibling::*"
    start_time_col = (
        f"{base_table}//th[contains(*/text(), 'Start Time')]/preceding-sibling::*"
    )
    status_xpath = (
        f"{base_table}//tbody/tr[position() <= 10]/td[count({status_col}) + 1]"
    )
    start_time_xpath = (
        f"{base_table}//tbody/tr[position() <= 10]/td[count({start_time_col}) + 1]"
    )

    statuses = [el.inner_text() for el in page.locator(f"xpath={status_xpath}").all()]
    start_times = [
        el.inner_text() for el in page.locator(f"xpath={start_time_xpath}").all()
    ]

    rows = list(zip(statuses, start_times))
    rows = [
        (s, t) for (s, t) in rows
        if not (
            (s == "INTERRUPTED" and (not t or t == "Task never started"))
            or s == "SKIPPED"
        )
    ]

    if not rows:
        return None

    first_status = rows[0][0]
    if first_status == "FINISHED":
        return True
    if first_status == "INTERRUPTED":
        raise AssertionError("Taskomatic task was INTERRUPTED")
    return None


# ---------------------------------------------------------------------------
# Content area text assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a "(?P<text>[^"]*)" text in the content area'))
def step_should_see_text_in_content_area(page, text: str):
    scope = page.locator("#spacewalk-content")
    assert scope.get_by_text(text).count() > 0, f"Text '{text}' not found in content area"


@then(parsers.re(r'I should not see a "(?P<text>[^"]*)" text in the content area'))
def step_should_not_see_text_in_content_area(page, text: str):
    scope = page.locator("#spacewalk-content")
    assert scope.get_by_text(text).count() == 0, f"Text '{text}' found in content area"


# ---------------------------------------------------------------------------
# Row-level click actions
# ---------------------------------------------------------------------------

@when(parsers.re(r'I click on "(?P<link>[^"]+)" in row "(?P<item>[^"]+)"'))
def step_click_in_row(page, link: str, item: str):
    row = page.locator(f"xpath=//tr[td[contains(.,'{item}')]]").first
    try:
        row.get_by_role("link", name=link).click()
    except Exception:
        row.get_by_role("button", name=link).click()


@when(parsers.re(r'I click on "(?P<button>[^"]+)" in tree item "(?P<item>.*?)"'))
def step_click_in_tree_item(page, button: str, item: str):
    xpath = (
        f"//span[contains(text(), '{item}')]"
        "/ancestor::div[contains(@class, 'product-details-wrapper')]"
    )
    scope = page.locator(f"xpath={xpath}").first
    try:
        scope.get_by_role("button", name=button).click()
    except Exception:
        scope.get_by_role("link", name=button).click()


# ---------------------------------------------------------------------------
# URL / path assertion
# ---------------------------------------------------------------------------

@then(parsers.re(r'the current path is "(?P<path>[^"]*)"'))
def step_current_path_is(page, path: str):
    from urllib.parse import urlparse
    current = urlparse(page.url).path
    assert current == path, f"Path {current} different than {path}"


# ---------------------------------------------------------------------------
# Wait for text variants
# ---------------------------------------------------------------------------

@when(parsers.re(r'I wait at most (?P<seconds>\d+) seconds until I see "(?P<text>[^"]*)" text$'))
def step_wait_at_most_seconds_see_text(page, seconds: str, text: str):
    assert check_text(page, text, timeout=int(seconds)), f"Text '{text}' not found"


@when(parsers.re(
    r'I wait until I see "(?P<text1>[^"]*)" text or "(?P<text2>[^"]*)" text'
    r'(?P<refresh_opt>(?:, refreshing the page)?)$'
))
def step_wait_until_see_text_or(page, text1: str, text2: str, refresh_opt: str):
    if refresh_opt:
        def _attempt():
            if check_text(page, text1, timeout=3) or check_text(page, text2, timeout=3):
                return True
            time.sleep(3)
            refresh_page(page)
            return None
        repeat_until_timeout(
            _attempt,
            message=f"Couldn't find text '{text1}' or text '{text2}'",
        )
    else:
        assert check_text(page, text1, timeout=DEFAULT_TIMEOUT) or \
               check_text(page, text2, timeout=DEFAULT_TIMEOUT), \
               f"Text '{text1}' and '{text2}' not found"


@when(parsers.re(
    r'I wait until I see "(?P<text>[^"]*)" (?P<type>text|regex), refreshing the page$'
))
def step_wait_until_see_text_refreshing(page, text: str, type: str):
    if type == "regex":
        pattern = re.compile(text)

        def _attempt():
            content = page.content()
            if pattern.search(content):
                return True
            refresh_page(page)
            return None
        repeat_until_timeout(_attempt, message=f"Couldn't find regex '{text}'")
    else:
        if check_text(page, text, timeout=3):
            return
        wait_for_text_refreshing(page, text)


@when(parsers.re(
    r'I wait at most (?P<seconds>\d+) seconds until I do not see "(?P<text>[^"]*)" text, '
    r'refreshing the page$'
))
def step_wait_not_see_text_refreshing_with_timeout(page, seconds: str, text: str):
    timeout = int(seconds)
    if not check_text(page, text, timeout=3):
        return

    def _attempt():
        if not check_text(page, text, timeout=3):
            return True
        refresh_page(page)
        return None
    repeat_until_timeout(
        _attempt,
        timeout=timeout,
        message=f"I still see text '{text}'",
    )


@when(parsers.re(
    r'I wait at most "(?P<seconds>[^"]*)" seconds until I do not see "(?P<text>[^"]*)" text$'
))
def step_wait_not_see_text_quoted_timeout(page, seconds: str, text: str):
    timeout = int(seconds)
    if not check_text(page, text, timeout=3):
        return

    def _attempt():
        return True if not check_text(page, text, timeout=3) else None
    repeat_until_timeout(
        _attempt,
        timeout=timeout,
        message=f"I still see text '{text}'",
    )


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until the event is completed, refreshing the page$'
))
def step_wait_event_completed(page, timeout: str):
    timeout_int = int(timeout)
    completed_text = "This action's status is: Completed."
    failed_text = "This action's status is: Failed."
    if check_text(page, completed_text, timeout=3):
        return

    last_log = time.time()

    def _attempt():
        nonlocal last_log
        if check_text(page, completed_text, timeout=3):
            return True
        if check_text(page, failed_text, timeout=3):
            details = page.locator(
                "xpath=//li[.//strong[text()='Details:']]//pre"
            ).all()
            combined = "\n".join(el.inner_text() for el in details)
            raise RuntimeError(f"Event failed. Details:\n{combined}")
        now = time.time()
        if now - last_log > 150:
            last_log = now
        refresh_page(page)
        return None
    repeat_until_timeout(
        _attempt,
        timeout=timeout_int,
        message="Event not yet completed",
    )


@when(parsers.re(r'I wait until I see the system name of "(?P<host>[^"]*)"$'))
def step_wait_until_see_system_name(page, host: str):
    system_name = get_system_name(host)
    wait_for_text(page, system_name)


@when(parsers.re(r'I wait until I see the "(?P<system_name>[^"]*)" system, refreshing the page$'))
def step_wait_until_see_system_refreshing(page, system_name: str):
    # First wait for "Loading..." to disappear
    def _not_loading():
        return True if not check_text(page, "Loading...", timeout=3) else None
    repeat_until_timeout(_not_loading, message="Still seeing 'Loading...'")
    wait_for_text_refreshing(page, system_name)


@when(parsers.re(r'I wait until I do not see "(?P<text>[^"]*)" text, refreshing the page$'))
def step_wait_until_not_see_text_refreshing(page, text: str):
    if not check_text(page, text, timeout=3):
        return

    def _attempt():
        if not check_text(page, text, timeout=3):
            return True
        refresh_page(page)
        return None
    repeat_until_timeout(_attempt, message=f"Text '{text}' is still visible")


@when(parsers.re(r'I wait until I do not see the name of "(?P<host>[^"]*)", refreshing the page$'))
def step_wait_until_not_see_name_refreshing(page, host: str):
    system_name = get_system_name(host)
    if not check_text(page, system_name, timeout=3):
        return

    def _attempt():
        if not check_text(page, system_name, timeout=3):
            return True
        refresh_page(page)
        return None
    repeat_until_timeout(_attempt, message=f"Text '{system_name}' is still visible")


@when(parsers.re(r'I wait until I see the (?P<type>VNC|spice) graphical console$'))
def step_wait_graphical_console(page, type: str):
    def _attempt():
        if page.locator("xpath=//canvas").count() > 0:
            return True
        if page.locator(
            "xpath=//*[contains(@class, 'modal-title') and text() = 'Failed to connect']"
        ).count() > 0:
            refresh_page(page)
        return None
    repeat_until_timeout(
        _attempt,
        message=f"The {type} graphical console didn't load",
    )


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------

@when("I switch to last opened window")
def step_switch_to_last_window(page, context):
    """Switch Playwright context to the most recently opened page."""
    pages = context.pages
    if len(pages) > 1:
        pages[-1].bring_to_front()


@when("I close the last opened window")
def step_close_last_window(page, context):
    pages = context.pages
    if len(pages) > 1:
        pages[-1].close()


# ---------------------------------------------------------------------------
# Checkbox / uncheck by id
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check "(?P<identifier>[^"]*)"$'))
def step_check_checkbox(page, identifier: str):
    cb = page.locator(f"#{identifier}, input[name='{identifier}']").first
    if not cb.is_checked():
        cb.check()
    assert cb.is_checked(), f"Checkbox {identifier} not checked."


@when(parsers.re(r'I uncheck "(?P<identifier>[^"]*)"$'))
def step_uncheck_checkbox(page, identifier: str):
    cb = page.locator(f"#{identifier}, input[name='{identifier}']").first
    if cb.is_checked():
        cb.uncheck()
    assert not cb.is_checked(), f"Checkbox {identifier} not unchecked."


@when(parsers.re(r'I (?P<action>check|uncheck) "(?P<label>[^"]*)" by label'))
def step_check_by_label(page, action: str, label: str):
    xpath = f"//label[text()='{label}']/preceding-sibling::input[@type='checkbox']"
    cb = page.locator(f"xpath={xpath}").first
    if action == "check":
        cb.set_checked(True)
        assert cb.is_checked(), f"Checkbox {label} not checked."
    else:
        cb.set_checked(False)
        assert not cb.is_checked(), f"Checkbox {label} not unchecked."


@when(parsers.re(r'I select the channel "(?P<channel>[^"]*)"$'))
def step_select_channel(page, channel: str):
    xpath = f"//a[text()='{channel}']/preceding-sibling::input[@type='checkbox']"
    cb = page.locator(f"xpath={xpath}").first
    cb.check()
    assert cb.is_checked(), f"Checkbox for channel '{channel}' not checked."


# ---------------------------------------------------------------------------
# Select from dropdown (enhanced variant with React fallback)
# ---------------------------------------------------------------------------

@when(parsers.re(r'I select the parent channel for the "(?P<client>[^"]*)" from "(?P<field>[^"]*)"'))
def step_select_parent_channel(page, client: str, field: str):
    from support.commonlib import product as get_product
    prod = get_product()
    channel = BASE_CHANNEL_BY_CLIENT.get(prod, {}).get(client, "")
    select_option_from_field(page, channel, field)


@when(parsers.re(r'I select "(?P<value>[^"]*)" from drop-down in table line with "(?P<line>[^"]*)"'))
def step_select_from_dropdown_in_table_line(page, value: str, line: str):
    xpath = (
        f"//div[contains(@class, 'table-responsive')]"
        f"//tr[contains(., '{line}')]//select"
    )
    dropdown = page.locator(f"xpath={xpath}").first
    dropdown.select_option(value)


# ---------------------------------------------------------------------------
# Radio button steps
# ---------------------------------------------------------------------------

@when(parsers.re(r'I choose "(?P<label_text>[^"]*)" radio button$'))
def step_choose_radio_button(page, label_text: str):
    rb = page.get_by_label(label_text).first
    rb.check()
    assert rb.is_checked(), f"Radio button '{label_text}' not checked."


@when(parsers.re(r'I choose radio button "(?P<radio>[^"]*)" for child channel "(?P<channel>[^"]*)"'))
def step_choose_radio_for_child_channel(page, radio: str, channel: str):
    xpath = f"//dt[contains(.//div, '{channel}')]//label[text()='{radio}']"
    label = page.locator(f"xpath={xpath}").first
    for_attr = label.get_attribute("for")
    page.locator(f"#{for_attr}").check()


@when("I wait for child channels to appear")
def step_wait_for_child_channels(page):
    for text in ["Loading...", "Loading child channels..", "Loading dependencies.."]:
        def _not_present(t=text):
            return True if not check_text(page, t, timeout=3) else None
        repeat_until_timeout(_not_present, message=f"Still seeing '{text}'")


@when(parsers.re(r'I (?P<action>include|exclude) the recommended child channels$'))
def step_include_exclude_recommended_channels(page, action: str):
    toggle_xpath = "//span[@class='pointer']"
    assert check_text(page, "include recommended", timeout=10), (
        "Could not find 'include recommended' text"
    )
    assert page.locator(f"xpath={toggle_xpath}").count() > 0, "The toggle is not present"

    if action == "include":
        toggle_off = "//i[contains(@class, 'fa-toggle-off')]"
        if page.locator(f"xpath={toggle_off}").count() > 0:
            page.locator(f"xpath={toggle_xpath}").first.click()
    else:
        toggle_on = "//i[contains(@class, 'fa-toggle-on')]"
        if page.locator(f"xpath={toggle_on}").count() > 0:
            page.locator(f"xpath={toggle_xpath}").first.click()


@when(parsers.re(r'I choose "(?P<value>[^"]*)"$'))
def step_choose_radio_by_value(page, value: str):
    page.locator(f"xpath=//input[@type='radio' and @value='{value}']").first.set_checked(True)


# ---------------------------------------------------------------------------
# Text entry variants
# ---------------------------------------------------------------------------

@when(parsers.re(r'I enter data from table with value as field name'))
def step_enter_data_from_table(page, datatable):
    for row in datatable:
        enter_text_in_field(page, row[0], row[1])


@when(parsers.re(r'I enter "(?P<text>[^"]*)" in the placeholder "(?P<placeholder>[^"]*)"'))
def step_enter_in_placeholder(page, text: str, placeholder: str):
    page.locator(f"input[placeholder='{placeholder}']").first.fill(text)


@when(parsers.re(r'I enter (?P<minutes>\d+) minutes from now as "(?P<field>[^"]*)"'))
def step_enter_minutes_from_now(page, minutes: str, field: str):
    from support.commonlib import get_future_time
    future_time = get_future_time(int(minutes))
    loc = page.locator(
        f'input[id="{field}"], input[name="{field}"], textarea[id="{field}"]'
    ).first
    loc.fill("")
    loc.fill(future_time)


@when(parsers.re(r'I enter "(?P<arg1>[^"]*)" as "(?P<arg2>[^"]*)" text area'))
def step_enter_as_textarea(page, arg1: str, arg2: str):
    page.evaluate(f"document.getElementsByName('{arg2}')[0].value = '{arg1}'")


@when(parsers.re(r'I enter "(?P<text>.*?)" as "(?P<field>.*?)" in the content area'))
def step_enter_as_in_content_area(page, text: str, field: str):
    scope = page.locator("xpath=//section")
    loc = scope.locator(
        f'input[id="{field}"], input[name="{field}"], textarea[id="{field}"]'
    ).first
    loc.fill(text)


@when(parsers.re(r'I enter the URI of the registry as "(?P<field>[^"]*)"'))
def step_enter_registry_uri(page, field: str):
    import os
    no_auth_registry = os.getenv("NO_AUTH_REGISTRY", "")
    enter_text_in_field(page, no_auth_registry, field)


@when(parsers.re(r'I enter "(?P<search_text>[^"]*)" on the search field$'))
def step_enter_on_search_field(page, search_text: str):
    enter_text_in_field(page, search_text, "search_string")


# ---------------------------------------------------------------------------
# Go back
# ---------------------------------------------------------------------------

@when("I go back")
def step_go_back(page):
    page.go_back()


# ---------------------------------------------------------------------------
# Button/link click variants
# ---------------------------------------------------------------------------

@when(parsers.re(r'I click on the inventory accordion for "(?P<text>[^"]*)"'))
def step_click_inventory_accordion(page, text: str):
    xpath = (
        f"//button[contains(@class, 'panel-heading') "
        f"and .//i[contains(@class, 'fa-chevron-right')] "
        f"and contains(., '{text}')]"
    )
    page.locator(f"xpath={xpath}").first.click()


@when(parsers.re(r'I click on "(?P<text>[^"]*)" in element "(?P<element_id>[^"]*)"'))
def step_click_in_element(page, text: str, element_id: str):
    scope = page.locator(f"xpath=//div[@id='{element_id}']").first
    try:
        scope.get_by_role("button", name=text).first.click()
    except Exception:
        scope.get_by_role("link", name=text).first.click()


@when(parsers.re(r'I click on "(?P<text>[^"]*)" and confirm$'))
def step_click_and_confirm(page, text: str):
    page.once("dialog", lambda dialog: dialog.accept())
    click_on(page, text)


@when(parsers.re(r'I click on "(?P<text>[^"]*)" and confirm alert box$'))
def step_click_and_confirm_alert(page, text: str):
    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name=text).first.click()


@when(parsers.re(r'I follow first "(?P<text>[^"]*)"$'))
@given(parsers.re(r'I follow first "(?P<text>[^"]*)"$'))
def step_follow_first_link(page, text: str):
    page.get_by_role("link", name=text).first.click()


@when(parsers.re(r'I follow "(?P<arg1>[^"]*)" in the (?P<arg2>.+)$'))
@given(parsers.re(r'I follow "(?P<arg1>[^"]*)" in the (?P<arg2>.+)$'))
def step_follow_in_section(page, arg1: str, arg2: str):
    tag_map = {
        "tab bar": "header", "tabs": "header", "content area": "section",
    }
    tag = None
    for key, val in tag_map.items():
        if key in arg2:
            tag = val
            break
    if tag is None:
        raise ValueError(f"Unknown element with description '{arg2}'")
    scope = page.locator(f"xpath=//{tag}")
    scope.get_by_role("link", name=arg1).first.click()
    wait_for_ajax(page)


@when(parsers.re(r'I follow first "(?P<arg1>[^"]*)" in the (?P<arg2>.+)$'))
def step_follow_first_in_section(page, arg1: str, arg2: str):
    tag_map = {
        "tab bar": "header", "tabs": "header", "content area": "section",
    }
    tag = None
    for key, val in tag_map.items():
        if key in arg2:
            tag = val
            break
    if tag is None:
        raise ValueError(f"Unknown element with description '{arg2}'")
    scope = page.locator(f"xpath=//{tag}")
    scope.get_by_role("link", name=arg1).first.click()


@when(parsers.re(r'I follow "(?P<text>[^"]*)" on "(?P<host>.*?)" row$'))
def step_follow_on_host_row(page, text: str, host: str):
    system_name = get_system_name(host)
    xpath = (
        f"//tr[td[contains(.,'{system_name}')]]//a[contains(., '{text}')]"
    )
    page.locator(f"xpath={xpath}").first.click()


@when(parsers.re(r'I enter "(?P<arg1>.*?)" in the editor$'))
def step_enter_in_editor(page, arg1: str):
    page.evaluate(f"ace.edit('contents-editor').insert('{arg1}')")


@when(parsers.re(r'I follow this "(?P<host>[^"]*)" link$'))
def step_follow_host_link(page, host: str):
    system_name = get_system_name(host)
    click_link_and_wait(page, system_name)


# ---------------------------------------------------------------------------
# Login / logout steps
# ---------------------------------------------------------------------------

@given(parsers.re(r'I am not authorized$'))
def step_not_authorized(page):
    xpath_logout = "//a[@href='/rhn/Logout.do']"
    if page.locator(f"xpath={xpath_logout}").count() > 0:
        page.locator(f"xpath={xpath_logout}").click()
    page.goto(APP_HOST, wait_until="domcontentloaded")
    assert page.get_by_role("button", name="Sign In").count() > 0, (
        "Button 'Sign In' not visible"
    )


@when("I go to the home page")
def step_go_home(page):
    page.goto(APP_HOST, wait_until="domcontentloaded")


@given("I access the host the first time")
def step_access_host_first_time(page):
    from support.commonlib import product as get_product
    page.goto(APP_HOST, wait_until="domcontentloaded")
    prod = get_product()
    assert check_text(page, f"Create {prod} Administrator"), (
        f"Text 'Create {prod} Administrator' not found"
    )


@given(parsers.re(r'I am authorized as "(?P<user>[^"]*)" with password "(?P<passwd>[^"]*)"'))
def step_authorized_as(page, user: str, passwd: str):
    authorize_user(page, user, passwd)


@given("I am authorized")
def step_authorized(page):
    authorize_user(page, "admin", "admin")


@when("I sign out")
def step_sign_out(page):
    page.locator("xpath=//a[@href='/rhn/Logout.do']").click()


@then("I should not be authorized")
def step_should_not_be_authorized(page):
    assert page.locator("xpath=//a[@href='/rhn/Logout.do']").count() == 0, (
        "User is authorized"
    )


@then("I should be logged in")
def step_should_be_logged_in(page):
    xpath = "//a[@href='/rhn/Logout.do']"
    page.locator(f"xpath={xpath}").wait_for(
        state="visible", timeout=DEFAULT_TIMEOUT * 3 * 1000
    )


@when("I am logged in")
def step_am_logged_in(page):
    assert page.locator("xpath=//a[@href='/rhn/Logout.do']").first.is_visible(), (
        "User is not logged in"
    )


# ---------------------------------------------------------------------------
# Navigate to systems pages
# ---------------------------------------------------------------------------

@given(parsers.re(r'I navigate to the Systems overview page of this "(?P<host>[^"]*)"'))
def step_navigate_systems_overview(page, api_test, host: str):
    system_name = get_system_name(host)
    # Go to systems page, search, click
    page.goto(f"{APP_HOST}/rhn/systems/Overview.do", wait_until="domcontentloaded")
    enter_text_in_field(page, system_name, "criteria")
    def _not_loading():
        return True if not check_text(page, "Loading...", timeout=3) else None
    repeat_until_timeout(_not_loading, message="Still seeing 'Loading...'")
    click_link_and_wait(page, system_name)
    assert check_text(page, "System Status", timeout=DEFAULT_TIMEOUT), (
        "System Status not found after navigation"
    )


@given(parsers.re(r'I am on the "(?P<pg>[^"]*)" page of this "(?P<host>[^"]*)"'))
def step_on_page_of_host(page, api_test, pg: str, host: str):
    system_id = _get_system_id(api_test, host)
    overview_url = f"/rhn/systems/details/Overview.do?sid={system_id}"
    page.goto(f"{APP_HOST}{overview_url}", wait_until="domcontentloaded")
    wait_for_ajax(page)
    follow_link_in_content_area(page, pg)


# ---------------------------------------------------------------------------
# Table row steps
# ---------------------------------------------------------------------------

@then(parsers.re(r'table row for "(?P<arg1>[^"]*)" should contain "(?P<arg2>[^"]*)"'))
def step_table_row_should_contain(page, arg1: str, arg2: str):
    xpath = f"//tr[.//*[contains(.,'{arg1}')]]"
    scope = page.locator(f"xpath={xpath}").first
    assert scope.get_by_text(arg2).count() > 0 or check_text(page, arg2, timeout=DEFAULT_TIMEOUT), (
        f"Row for '{arg1}' does not contain '{arg2}'"
    )


@when(parsers.re(r'I wait until table row for "(?P<arg1>[^"]*)" contains "(?P<arg2>[^"]*)"'))
def step_wait_table_row_contains(page, arg1: str, arg2: str):
    xpath = f"//tr[.//*[contains(.,'{arg1}')]]"
    scope = page.locator(f"xpath={xpath}").first

    def _attempt():
        try:
            return True if scope.get_by_text(arg2).count() > 0 else None
        except Exception:
            return None
    repeat_until_timeout(
        _attempt,
        message=f"Row for '{arg1}' does not contain '{arg2}'",
    )


@then(parsers.re(
    r'the table row for "(?P<row>[^"]*)" should(?P<should_not> not)? contain "(?P<icon>[^"]*)" icon'
))
def step_table_row_has_icon(page, row: str, should_not: str, icon: str):
    if icon == "retracted":
        selector = "i[class*='errata-retracted']"
    else:
        raise ValueError(f"Unsupported icon '{icon}'")
    xpath = f"//tr[.//*[contains(.,'{row}')]]"
    scope = page.locator(f"xpath={xpath}").first
    if should_not:
        assert scope.locator(selector).count() == 0, (
            f"Row for '{row}' has icon '{icon}'"
        )
    else:
        assert scope.locator(selector).count() > 0, (
            f"Row for '{row}' does not have icon '{icon}'"
        )


@when(parsers.re(
    r'I wait at most (?P<timeout>[0-9]+) seconds until table row for "(?P<text>[^"]*)" '
    r'contains button "(?P<button>[^"]*)"'
))
def step_wait_table_row_has_button(page, timeout: str, text: str, button: str):
    xpath = (
        f"//tr[td[contains(., '{text}')]]/td/descendant::*"
        f"[self::a or self::button][@title='{button}']"
    )
    page.locator(f"xpath={xpath}").first.wait_for(
        state="visible", timeout=int(timeout) * 1000
    )


@when(parsers.re(r'I wait until table row for "(?P<text>[^"]*)" contains button "(?P<button>[^"]*)"'))
def step_wait_table_row_has_button_default(page, text: str, button: str):
    xpath = (
        f"//tr[td[contains(., '{text}')]]/td/descendant::*"
        f"[self::a or self::button][@title='{button}']"
    )
    page.locator(f"xpath={xpath}").first.wait_for(
        state="visible", timeout=DEFAULT_TIMEOUT * 1000
    )


@when(parsers.re(r'I wait until table row contains a "(?P<text>[^"]*)" text$'))
def step_wait_table_row_contains_text(page, text: str):
    xpath = f"//tr[.//td[contains(.,'{text}')]]"
    page.locator(f"xpath={xpath}").first.wait_for(
        state="visible", timeout=DEFAULT_TIMEOUT * 1000
    )


@when(parsers.re(r'I wait until button "(?P<text>[^"]*)" becomes enabled$'))
def step_wait_button_enabled(page, text: str):
    def _attempt():
        btn = page.get_by_role("button", name=text).first
        return True if not btn.is_disabled() else None
    repeat_until_timeout(
        _attempt,
        message=f"Button '{text}' still disabled after {DEFAULT_TIMEOUT} seconds",
    )


# ---------------------------------------------------------------------------
# Update check
# ---------------------------------------------------------------------------

@then("I should see an update in the list")
def step_should_see_update_in_list(page):
    xpath = "//div[@class='table-responsive']//tr/td/a"
    assert page.locator(f"xpath={xpath}").count() > 0, f"xpath: {xpath} not found"


# ---------------------------------------------------------------------------
# Checkbox helpers in lists
# ---------------------------------------------------------------------------

@when("I check test channel")
def step_check_test_channel(page):
    toggle_checkbox_in_list(page, "check", "Fake-Base-Channel-SUSE-like")


@when(parsers.re(r'I check "(?P<arg1>[^"]*)" patch$'))
def step_check_patch(page, arg1: str):
    toggle_checkbox_in_list(page, "check", arg1)


@then(parsers.re(r'I should see "(?P<arg>[^"]*)" systems selected for SSM$'))
def step_should_see_ssm_count(page, arg: str):
    scope = page.locator("xpath=//span[@id='spacewalk-set-system_list-counter']")
    assert scope.get_by_text(arg).count() > 0 or check_text(page, arg, timeout=3), (
        f"There are not {arg} systems selected"
    )


# ---------------------------------------------------------------------------
# Text assertions (not/or variants)
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a "(?P<text1>[^"]*)" text or "(?P<text2>[^"]*)" text$'))
def step_should_see_text_or(page, text1: str, text2: str):
    assert check_text(page, text1, timeout=3) or check_text(page, text2, timeout=3), (
        f"Text '{text1}' and '{text2}' not found"
    )


@then(parsers.re(r'I should not see "(?P<host>[^"]*)" hostname$'))
def step_should_not_see_hostname(page, host: str):
    system_name = get_system_name(host)
    assert not check_text(page, system_name, timeout=3), (
        f"Hostname {system_name} is present"
    )


# ---------------------------------------------------------------------------
# Textarea assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see "(?P<text>[^"]*)" in the textarea$'))
def step_should_see_in_textarea(page, text: str):
    content = page.locator("textarea").first.input_value()
    assert text in content, f"Text '{text}' not found in textarea"


@then(parsers.re(r'I should see "(?P<text1>[^"]*)" or "(?P<text2>[^"]*)" in the textarea$'))
def step_should_see_or_in_textarea(page, text1: str, text2: str):
    content = page.locator("textarea").first.input_value()
    assert text1 in content or text2 in content, (
        f"Text '{text1}' and '{text2}' not found in textarea"
    )


@then(parsers.re(r'I should see "(?P<text>[^"]*)" in the (?P<id>[^ ]+) textarea$'))
def step_should_see_in_named_textarea(page, text: str, id: str):
    content = page.locator(f"xpath=.//textarea[@data-testid='{id}']").first.input_value()
    assert text in content, f"Text '{text}' not found in textarea '{id}'"


@then(parsers.re(
    r'I should see "(?P<text1>[^"]*)" or "(?P<text2>[^"]*)" in the (?P<id>[^ ]+) textarea$'
))
def step_should_see_or_in_named_textarea(page, text1: str, text2: str, id: str):
    content = page.locator(f"xpath=.//textarea[@data-testid='{id}']").first.input_value()
    assert text1 in content or text2 in content, (
        f"Text '{text1}' and '{text2}' not found in textarea '{id}'"
    )


# ---------------------------------------------------------------------------
# Regex text assertion
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a text like "(?P<title>[^"]*)"$'))
def step_should_see_text_like(page, title: str):
    pattern = re.compile(title)
    content = page.content()
    assert pattern.search(content), f"Regular expression '{title}' not found"


# ---------------------------------------------------------------------------
# Not-present text assertion
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should not see a "(?P<text>[^"]*)" text$'))
def step_should_not_see_text(page, text: str):
    assert not check_text(page, text, timeout=3), (
        f"Text '{text}' found on the page"
    )


# ---------------------------------------------------------------------------
# Link assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a "(?P<text>[^"]*)" link$'))
def step_should_see_link(page, text: str):
    assert page.get_by_role("link", name=text).count() > 0, (
        f"Link {text} is not visible"
    )


@then(parsers.re(r'I should not see a "(?P<arg1>[^"]*)" link$'))
def step_should_not_see_link(page, arg1: str):
    assert page.get_by_role("link", name=arg1).count() == 0, (
        f"Link {arg1} is present"
    )


@then(parsers.re(r'I should see a "(?P<arg1>[^"]*)" button$'))
def step_should_see_button(page, arg1: str):
    btn = page.get_by_role("button", name=arg1).first
    assert btn.is_visible(), f"Button {arg1} is not visible"


@then(parsers.re(r'I should see a "(?P<linktext>.*?)" link in the text$'))
def step_should_see_link_in_text(page, linktext: str, datatable):
    text = datatable[0][0]
    xpath = f"//p/strong[contains(normalize-space(string(.)), '{text}')]"
    scope = page.locator(f"xpath={xpath}").first
    assert scope.locator(f"xpath=//a[text() = '{linktext}']").count() > 0


@then(parsers.re(r'I should see a "(?P<text>[^"]*)" text in element "(?P<element>[^"]*)"'))
def step_should_see_text_in_element(page, text: str, element: str):
    scope = page.locator(
        f'xpath=//div[@id="{element}" or @class="{element}"]'
    ).first
    assert scope.get_by_text(text).count() > 0, (
        f"Text '{text}' not found in {element}"
    )


@then(parsers.re(r'I should not see a "(?P<text>[^"]*)" text in element "(?P<element>[^"]*)"'))
def step_should_not_see_text_in_element(page, text: str, element: str):
    scope = page.locator(
        f'xpath=//div[@id="{element}" or @class="{element}"]'
    ).first
    assert scope.get_by_text(text).count() == 0, (
        f"Text '{text}' found in {element}"
    )


@then(parsers.re(
    r'I should see a "(?P<text1>[^"]*)" or "(?P<text2>[^"]*)" text in element "(?P<element>[^"]*)"'
))
def step_should_see_text_or_in_element(page, text1: str, text2: str, element: str):
    scope = page.locator(
        f'xpath=//div[@id="{element}" or @class="{element}"]'
    ).first
    assert (
        scope.get_by_text(text1).count() > 0 or
        scope.get_by_text(text2).count() > 0
    ), f"Texts {text1} and {text2} not found in {element}"


@then(parsers.re(
    r'I should see a "(?P<link>[^"]*)" link in the table (?P<column>.*) column$'
))
def step_should_see_link_in_table_column(page, link: str, column: str):
    ordinals = ["first", "second", "third", "fourth"]
    if column in ordinals:
        idx = ordinals.index(column)
    else:
        colname = column.strip("'\"")
        headers = page.locator("xpath=//table//thead/tr[1]/th").all()
        cols = [h.inner_text() for h in headers]
        assert colname in cols, f"Unknown column '{column}'"
        idx = cols.index(colname)
    xpath = f"//table//tr/td[{idx + 1}]//a[text()='{link}']"
    assert page.locator(f"xpath={xpath}").count() > 0, (
        f"Link '{link}' not found in column {column}"
    )


@then(parsers.re(
    r'I should see a "(?P<arg1>[^"]*)" link in the (?P<arg2>left menu|tab bar|tabs|content area)$'
))
def step_should_see_link_in_section(page, arg1: str, arg2: str):
    tag_map = {"left menu": "aside", "tab bar": "header", "tabs": "header", "content area": "section"}
    tag = tag_map.get(arg2)
    if not tag:
        raise ValueError(f"Unknown element with description '{arg2}'")
    scope = page.locator(f"xpath=//{tag}")
    assert scope.get_by_role("link", name=arg1).count() > 0, (
        f"Link '{arg1}' not found in {arg2}"
    )


@then(parsers.re(
    r'I should not see a "(?P<arg1>[^"]*)" link in the (?P<arg2>.+)$'
))
def step_should_not_see_link_in_section(page, arg1: str, arg2: str):
    tag_map = {"left menu": "aside", "tab bar": "header", "tabs": "header", "content area": "section"}
    tag = None
    for key, val in tag_map.items():
        if key in arg2:
            tag = val
            break
    if not tag:
        raise ValueError(f"Unknown element with description '{arg2}'")
    scope = page.locator(f"xpath=//{tag}")
    assert scope.get_by_role("link", name=arg1).count() == 0, (
        f"Link '{arg1}' found in {arg2}"
    )


@then(parsers.re(
    r'I should see a "(?P<arg1>[^"]*)" link in row (?P<arg2>[0-9]+) of the content menu$'
))
def step_should_see_link_in_content_menu_row(page, arg1: str, arg2: str):
    scope = page.locator("xpath=//section").first
    nav_scope = scope.locator(
        f"xpath=//div[@class='spacewalk-content-nav']/ul[{arg2}]"
    ).first
    assert nav_scope.get_by_role("link", name=arg1).count() > 0, (
        f"Link '{arg1}' not found in content menu row {arg2}"
    )


@then(parsers.re(r'I should see a "(?P<arg1>[^"]*)" button in "(?P<arg2>[^"]*)" form$'))
def step_should_see_button_in_form(page, arg1: str, arg2: str):
    scope = page.locator(
        f"xpath=//form[@id='{arg2}' or @name='{arg2}']"
    ).first
    assert scope.get_by_role("button", name=arg1).count() > 0, (
        f"Button {arg1} not found in form {arg2}"
    )


# ---------------------------------------------------------------------------
# Product list check
# ---------------------------------------------------------------------------

@then("I should only see success signs in the product list")
def step_only_success_in_product_list(page):
    assert page.locator("xpath=//*[contains(@class, 'fa-check-circle')]").count() > 0, (
        "No product synchronized"
    )
    assert page.locator("xpath=//*[contains(@class, 'fa-spinner')]").count() == 0, (
        "At least one product is not fully synchronized"
    )
    assert page.locator("xpath=//*[contains(@class, 'fa-exclamation-triangle')]").count() == 0, (
        "Warning detected"
    )
    assert page.locator("xpath=//*[contains(@class, 'fa-exclamation-circle')]").count() == 0, (
        "Error detected"
    )


# ---------------------------------------------------------------------------
# Repo / row checkbox helpers
# ---------------------------------------------------------------------------

@when(parsers.re(r'I select the "(?P<repo>[^"]*)" repo$'))
def step_select_repo(page, repo: str):
    toggle_checkbox_in_list(page, "check", repo)


@when(parsers.re(r'I check the row with the "(?P<text>[^"]*)" link$'))
def step_check_row_with_link(page, text: str):
    toggle_checkbox_in_list(page, "check", text)


@when(parsers.re(r'I check the row with the "(?P<text>[^"]*)" text$'))
def step_check_row_with_text(page, text: str):
    toggle_checkbox_in_list(page, "check", text)


@when("I check the first patch in the list, that does not require a reboot")
def step_check_first_patch_no_reboot(page):
    row = page.locator(
        "xpath=//section//div[@class='table-responsive']//tr"
    ).first
    reboot_required = row.locator(
        "xpath=.//*[contains(@title,'Reboot Required')]"
    ).count() > 0
    if reboot_required:
        # check second row
        second_row = page.locator(
            "xpath=//section//div[@class='table-responsive']//tr"
        ).nth(1)
        second_row.locator("xpath=.//input[@type='checkbox']").first.check()
    else:
        row.locator("xpath=.//input[@type='checkbox']").first.check()


# ---------------------------------------------------------------------------
# UI specific click helpers
# ---------------------------------------------------------------------------

@when("I click on the Legal button")
def step_click_legal_button(page):
    page.locator("xpath=//li[.//span[text()='Legal']]//button").first.click()


@when("I click on the red confirmation button")
def step_click_red_confirmation(page):
    page.locator("button.btn-danger").first.click()


@when("I click on the filter button until page does not contain")
def step_click_filter_until_not_contains_noop(page):
    """This step is superseded by the parsers.re variant below."""


@then(parsers.re(
    r'I click on the filter button until page does not contain "(?P<text>[^"]*)" text'
))
def step_click_filter_until_not_contains(page, text: str):
    def _attempt():
        if not check_text(page, text, timeout=3):
            return True
        try:
            page.locator("button.spacewalk-button-filter").click()
            check_text(page, "is filtered", timeout=3)
        except Exception:
            pass
        return None
    repeat_until_timeout(
        _attempt,
        message=f"'{text}' still found",
    )


# ---------------------------------------------------------------------------
# Filtered input fields
# ---------------------------------------------------------------------------

@when(parsers.re(r'I enter the hostname of "(?P<host>[^"]*)" as the filtered system name$'))
def step_enter_hostname_as_filtered_system_name(page, host: str):
    system_name = get_system_name(host)
    page.locator("input[placeholder='Filter by System Name: ']").first.fill(system_name)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered latest package$'))
def step_enter_filtered_latest_package(page, input: str):
    assert input, "Package name is not set"
    page.locator("input[placeholder='Filter by Package Name: ']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered synopsis$'))
def step_enter_filtered_synopsis(page, input: str):
    page.locator("input[placeholder='Filter by Synopsis: ']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered channel name$'))
def step_enter_filtered_channel_name(page, input: str):
    page.locator("input[placeholder='Filter by Channel Name: ']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered product description$'))
def step_enter_filtered_product_description(page, input: str):
    page.locator("input[name='product-description-filter']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered XCCDF result type$'))
def step_enter_filtered_xccdf(page, input: str):
    page.locator("input[placeholder='Filter by Result: ']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered snippet name$'))
def step_enter_filtered_snippet_name(page, input: str):
    page.locator("input[placeholder='Filter by Snippet Name: ']").first.fill(input)


@when(parsers.re(r'I enter "(?P<input>[^"]*)" as the filtered formula name$'))
def step_enter_filtered_formula_name(page, input: str):
    page.locator("input[placeholder='Filter by formula name']").first.fill(input)


@when(parsers.re(r'I enter the package for "(?P<host>[^"]*)" as the filtered package name$'))
def step_enter_package_for_host_filtered(page, host: str):
    pkg = PACKAGE_BY_CLIENT.get(host, "")
    filter_by_package_name(page, pkg)


@when(parsers.re(
    r'I check the package(?P<version_flag>| last version) for "(?P<host>[^"]*)" in the list$'
))
def step_check_package_for_host(page, version_flag: str, host: str):
    pkg = PACKAGE_BY_CLIENT.get(host, "")
    toggle_checkbox_in_package_list(
        page, "check", pkg, last_version=bool(version_flag.strip())
    )


@when(parsers.re(r'I check row with "(?P<text>[^"]*)" and arch of "(?P<client>[^"]*)"'))
def step_check_row_with_arch_of_client(page, text: str, client: str):
    arch = PKGARCH_BY_CLIENT.get(client, "")
    xpath = (
        f"//div[contains(@class, 'table-responsive')]"
        f"//tr[.//td[contains(.,'{text}')] and .//td[contains(.,'{arch}')]]"
        f"//input[@type='checkbox']"
    )
    page.locator(f"xpath={xpath}").first.set_checked(True)


@when(parsers.re(r'I uncheck row with "(?P<text>[^"]*)" and arch of "(?P<client>[^"]*)"'))
def step_uncheck_row_with_arch_of_client(page, text: str, client: str):
    arch = PKGARCH_BY_CLIENT.get(client, "")
    xpath = (
        f"//div[contains(@class, 'table-responsive')]"
        f"//tr[.//td[contains(.,'{text}')] and .//td[contains(.,'{arch}')]]"
        f"//input[@type='checkbox']"
    )
    page.locator(f"xpath={xpath}").first.set_checked(False)


@when(parsers.re(r'I check row with "(?P<text1>[^"]*)" and "(?P<text2>[^"]*)" in the list$'))
def step_check_row_with_two_texts(page, text1: str, text2: str):
    xpath = (
        f"//div[contains(@class, 'table-responsive')]"
        f"//tr[.//td[contains(.,'{text1}')] and .//td[contains(.,'{text2}')]]"
        f"//input[@type='checkbox']"
    )
    page.locator(f"xpath={xpath}").first.set_checked(True)


@when(parsers.re(r'I uncheck row with "(?P<text1>[^"]*)" and "(?P<text2>[^"]*)" in the list$'))
def step_uncheck_row_with_two_texts(page, text1: str, text2: str):
    xpath = (
        f"//div[contains(@class, 'table-responsive')]"
        f"//tr[.//td[contains(.,'{text1}')] and .//td[contains(.,'{text2}')]]"
        f"//input[@type='checkbox']"
    )
    page.locator(f"xpath={xpath}").first.set_checked(False)


@when("I check the second row in the list")
def step_check_second_row(page):
    scope = page.locator("xpath=//section").first
    row = scope.locator(
        "xpath=//div[@class='table-responsive']//tr[2]/td"
    ).first
    row.locator("xpath=.//input[@type='checkbox']").first.set_checked(True)


@when("I check the first row in the list")
def step_check_first_row(page):
    scope = page.locator("xpath=//section").first
    row = scope.locator(
        "xpath=//div[@class='table-responsive']//tr[.//td]"
    ).first
    row.locator("xpath=.//input[@type='checkbox']").first.set_checked(True)


@when(parsers.re(
    r'I (?P<check_option>check|uncheck) "(?P<text>[^"]*)"(?P<version_flag>| last version) in the list$'
))
def step_check_or_uncheck_in_list(page, check_option: str, text: str, version_flag: str):
    toggle_checkbox_in_package_list(
        page, check_option, text, last_version=bool(version_flag.strip())
    )


@when(parsers.re(r'I (?P<check_option>check|uncheck) the "(?P<text>[^"]*)" CLM filter$'))
def step_check_clm_filter(page, check_option: str, text: str):
    scope = page.locator("xpath=//div[@class='modal-body']").first
    xpath = f".//label[contains(text(), '{text}')]/input[@type='checkbox']"
    cb = scope.locator(f"xpath={xpath}").first
    assert cb.count() > 0, f"{text} CLM filter not found"
    cb.set_checked(check_option == "check")


# ---------------------------------------------------------------------------
# Option / radio button state checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'option "(?P<option>[^"]*)" is selected as "(?P<field>[^"]*)"$'))
def step_option_is_selected(page, option: str, field: str):
    # Standard select
    std_loc = page.locator(
        f':is(select)[id="{field}"], select[name="{field}"]'
    ).first
    if std_loc.count() > 0:
        selected = std_loc.evaluate("el => el.value")
        opts = std_loc.locator("option").all()
        for opt in opts:
            if opt.evaluate("el => el.selected"):
                if option in opt.inner_text():
                    return
    # React custom selector
    react_xpath = (
        f"//*[contains(@class, 'data-testid-{field}-child__value-container')]"
        f"/*[contains(text(),'{option}')]"
    )
    if page.locator(f"xpath={react_xpath}").count() > 0:
        return
    raise AssertionError(f"{option} is not selected as {field}")


@when(parsers.re(r'I wait until option "(?P<option>[^"]*)" appears in list "(?P<field>[^"]*)"$'))
def step_wait_option_in_list(page, option: str, field: str):
    def _attempt():
        std = page.locator(f':is(select)[id="{field}"], select[name="{field}"]').first
        if std.count() > 0:
            opts = std.locator("option").all()
            if any(option in opt.inner_text() for opt in opts):
                return True
        react_xpath = (
            f"//*[contains(@class, 'data-testid-{field}-child__value-container')]"
            f"/*[contains(text(),'{option}')]"
        )
        if page.locator(f"xpath={react_xpath}").count() > 0:
            return True
        return None
    repeat_until_timeout(
        _attempt,
        message=f"{option} has not been listed in {field}",
    )


@then(parsers.re(r'radio button "(?P<arg1>[^"]*)" should be checked$'))
def step_radio_should_be_checked(page, arg1: str):
    rb = page.get_by_label(arg1).first
    assert rb.is_checked(), f"{arg1} is unchecked"


@then(parsers.re(r'I should see "(?P<arg1>[^"]*)" as checked$'))
def step_should_see_as_checked(page, arg1: str):
    cb = page.get_by_label(arg1).first
    assert cb.is_checked(), f"{arg1} is unchecked"


@then(parsers.re(r'I should see "(?P<arg1>[^"]*)" as unchecked$'))
def step_should_see_as_unchecked(page, arg1: str):
    cb = page.get_by_label(arg1).first
    assert not cb.is_checked(), f"{arg1} is checked"


@then(parsers.re(r'the "(?P<arg1>[^"]*)" checkbox should be disabled$'))
def step_checkbox_should_be_disabled(page, arg1: str):
    assert page.locator(f"css=#{arg1}[disabled]").count() > 0


@then(parsers.re(r'the "(?P<arg1>[^"]*)" field should be disabled$'))
def step_field_should_be_disabled(page, arg1: str):
    assert page.locator(f"css=#{arg1}[disabled]").count() > 0


# ---------------------------------------------------------------------------
# Field value assertions
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see "(?P<text>[^"]*)" in field identified by "(?P<field>[^"]*)"$'))
def step_should_see_in_field(page, text: str, field: str):
    loc = page.locator(
        f'input[id="{field}"], input[name="{field}"], '
        f'textarea[id="{field}"], textarea[name="{field}"]'
    ).first
    value = loc.input_value()
    assert text in value, f"'{text}' not found in {field}"


@then(parsers.re(r'I should see a "(?P<field>[^"]*)" field in "(?P<form>[^"]*)" form$'))
def step_should_see_field_in_form(page, field: str, form: str):
    scope = page.locator(
        f'xpath=//form[@id="{form}"] | //form[@name="{form}"]'
    ).first
    assert scope.get_by_label(field).count() > 0 or \
           scope.locator(f'[id="{field}"], [name="{field}"]').count() > 0, (
        f"Field {field} not found in form {form}"
    )


@then(parsers.re(r'I should see a "(?P<editor>[^"]*)" editor in "(?P<form>[^"]*)" form$'))
def step_should_see_editor_in_form(page, editor: str, form: str):
    scope = page.locator(
        f'xpath=//form[@id="{form}"] | //form[@name="{form}"]'
    ).first
    assert scope.locator(f"textarea#{editor}").count() > 0, (
        f"textarea#{editor} not found"
    )
    assert scope.locator(f"#{editor}-editor").count() > 0, (
        f"#{editor}-editor not found"
    )


@then("I should see a Sign Out link")
def step_should_see_sign_out_link(page):
    assert page.locator("xpath=//a[@href='/rhn/Logout.do']").count() > 0


@then(parsers.re(
    r'I should see (?P<count>\d+) "(?P<name>[^"]*)" fields in "(?P<id>[^"]*)" form$'
))
def step_should_see_n_fields_in_form(page, count: str, name: str, id: str):
    scope = page.locator(
        f'xpath=//form[@id="{id}" or @name="{id}"]'
    ).first
    actual = scope.locator(
        f'[name="{name}"], [id="{name}"]'
    ).count()
    assert actual == int(count), (
        f"{id} form has not {count} fields with name {name} (found {actual})"
    )


# ---------------------------------------------------------------------------
# Modal dialog steps
# ---------------------------------------------------------------------------

@when(parsers.re(r'I click on "(?P<btn>[^"]*)" in "(?P<title>[^"]*)" modal$'))
def step_click_in_modal(page, btn: str, title: str):
    path = (
        f'//*[text() = "{title}"]'
        '/ancestor::div[contains(@class, "modal-dialog")]'
    )
    # Wait for modal to appear
    def _modal_visible():
        return True if page.locator(f"xpath={path}").count() > 0 else None
    repeat_until_timeout(
        _modal_visible,
        message=f"It couldn't find the {title} modal dialog",
    )
    scope = page.locator(f"xpath={path}").first
    scope.get_by_role("button", name=btn).click()
    # Wait for modal to disappear
    def _modal_gone():
        return True if page.locator(f"xpath={path}").count() == 0 else None
    repeat_until_timeout(
        _modal_gone,
        message=f"The {title} modal dialog is still present",
    )


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until I see modal containing "(?P<title>[^"]*)" text$'
))
def step_wait_modal_containing(page, timeout: str, title: str):
    path = (
        f'//*[contains(@class, "modal-content") and contains(., "{title}")]'
        '/ancestor::div[contains(@class, "modal-dialog")]'
    )
    page.locator(f"xpath={path}").first.wait_for(
        state="visible", timeout=int(timeout) * 1000
    )


# ---------------------------------------------------------------------------
# Exporter checkboxes
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check "(?P<exporter_type>[^"]*)" exporter$'))
def step_check_exporter(page, exporter_type: str):
    cb_id = f"exporters#{exporter_type}_exporter#enabled"
    toggle_checkbox(page, "check", cb_id)


@when("I check the blackbox exporter")
def step_check_blackbox_exporter(page):
    toggle_checkbox(page, "check", "prometheus#blackbox_exporter#enabled")


# ---------------------------------------------------------------------------
# Service endpoint visit
# ---------------------------------------------------------------------------

@when(parsers.re(r'I visit "(?P<service>[^"]*)" endpoint of this "(?P<host>[^"]*)"'))
def step_visit_service_endpoint(page, service: str, host: str):
    node = get_target(host)
    system_name = get_system_name(host)
    services = {
        "Proxy":                    (443,  "https", "/pub/",   "Index of /pub"),
        "Prometheus":               (9090, "http",  "/query",  "Prometheus Time Series Collection"),
        "Prometheus node exporter": (9100, "http",  "",        "Node Exporter"),
        "Prometheus apache exporter": (9117, "http", "",       "Apache Exporter"),
        "Prometheus postgres exporter": (9187, "http", "",     "Postgres Exporter"),
        "Grafana":                  (3000, "http",  "",        "Grafana Labs"),
    }
    if service not in services:
        raise ValueError(f"Unknown port for service {service}")
    port, protocol, path, text = services[service]
    os_family = getattr(node, "os_family", "")
    url = f"{protocol}://{system_name}:{port}{path}"
    if "debian" in os_family.lower() or "ubuntu" in os_family.lower():
        node.run_until_ok(f"wget --no-check-certificate -qO- {url} | grep -i '{text}'")
    else:
        node.run_until_ok(f"curl -s -k {url} | grep -i '{text}'")


@when(parsers.re(r'I enter the "(?P<host>[^"]*)" hostname as the Prometheus URL$'))
def step_enter_prometheus_url(page, host: str):
    node = get_target(host)
    enter_text_in_field(page, f"http://{node.full_hostname}:9090", "Prometheus URL")


# ---------------------------------------------------------------------------
# Maintenance window
# ---------------------------------------------------------------------------

@when("I select the next maintenance window")
def step_select_next_maintenance_window(page):
    page.locator(
        "xpath=//select[@id='maintenance-window-select']/option"
    ).first.click()


# ---------------------------------------------------------------------------
# Redfish / controller hostname
# ---------------------------------------------------------------------------

@when("I enter the controller hostname as the redfish server address")
def step_enter_controller_hostname_redfish(page):
    import subprocess
    hostname = subprocess.check_output(["hostname", "-f"]).decode().strip()
    enter_text_in_field(page, f"{hostname}:8443", "powerAddress")


# ---------------------------------------------------------------------------
# Browser management
# ---------------------------------------------------------------------------

@when("I clear browser cookies")
def step_clear_browser_cookies(page):
    page.context.clear_cookies()


@when("I close the modal dialog")
def step_close_modal_dialog(page):
    page.locator(
        "xpath=//*[contains(@class, 'modal-header')]"
        "/button[contains(@class, 'close')]"
    ).first.click()


@when("I refresh the page")
def step_refresh_page(page):
    page.once("dialog", lambda dialog: dialog.accept())
    page.evaluate("window.location.reload()")


# ---------------------------------------------------------------------------
# System list snapshot
# ---------------------------------------------------------------------------

@when("I make a list of the existing systems")
def step_make_list_of_systems(page, shared_state):
    elements = page.locator("xpath=//td[contains(@class, 'sortedCol')]").all()
    shared_state["systems_list"] = [el.inner_text() for el in elements]


# ---------------------------------------------------------------------------
# Property steps
# ---------------------------------------------------------------------------

@given(parsers.re(
    r'I have a property "(?P<property_name>[^"]*)" with value "(?P<property_value>[^"]*)" '
    r'on "(?P<host>[^"]*)"$'
))
def step_have_property(page, api_test, property_name: str, property_value: str, host: str):
    system_id = _get_system_id(api_test, host)
    overview_url = f"/rhn/systems/details/Overview.do?sid={system_id}"
    page.goto(f"{APP_HOST}{overview_url}", wait_until="domcontentloaded")
    follow_link_in_content_area(page, "Properties")
    enter_text_in_field(page, property_value, property_name)
    click_on(page, "Update Properties")
    assert check_text(page, "System properties changed", timeout=DEFAULT_TIMEOUT)


@given(parsers.re(
    r'I have a combobox property "(?P<property_name>[^"]*)" with value "(?P<property_value>[^"]*)" '
    r'on "(?P<host>[^"]*)"$'
))
def step_have_combobox_property(page, api_test, property_name: str, property_value: str, host: str):
    system_id = _get_system_id(api_test, host)
    overview_url = f"/rhn/systems/details/Overview.do?sid={system_id}"
    page.goto(f"{APP_HOST}{overview_url}", wait_until="domcontentloaded")
    follow_link_in_content_area(page, "Properties")
    select_option_from_field(page, property_value, property_name)
    click_on(page, "Update Properties")
    assert check_text(page, "System properties changed", timeout=DEFAULT_TIMEOUT)


# ---------------------------------------------------------------------------
# System overview landing assertion
# ---------------------------------------------------------------------------

@then("I should land on system's overview page")
def step_should_land_on_system_overview(page):
    for text in ["System Status", "System Info", "System Events", "System Properties",
                 "Subscribed Channels"]:
        assert check_text(page, text, timeout=DEFAULT_TIMEOUT), (
            f"Expected text '{text}' not found on system overview page"
        )


# ---------------------------------------------------------------------------
# Search button
# ---------------------------------------------------------------------------

@when("I click on the search button")
def step_click_search_button(page):
    click_button_and_wait(page, "Search")
    if check_text(page, "Could not connect to search server.", timeout=0):
        def _attempt():
            if check_text(page, "Could not connect to search server.", timeout=0):
                return None
            if check_text(page, "No matches found", timeout=0):
                return None
            return True
        repeat_until_timeout(
            _attempt,
            timeout=10,
            message="Could not perform a successful search after reindexation",
        )


@when(parsers.re(r'I enter "(?P<host>[^"]*)" hostname on the search field$'))
def step_enter_hostname_on_search_field(page, host: str):
    system_name = get_system_name(host)
    enter_text_in_field(page, system_name, "search_string")


# ---------------------------------------------------------------------------
# Grafana
# ---------------------------------------------------------------------------

@when(parsers.re(r"I enter \"(?P<host>[^\"]*)\" hostname on grafana's host field$"))
def step_enter_hostname_grafana(page, host: str):
    import re as _re
    system_name = get_system_name(host)
    current_url = page.url
    updated_url = _re.sub(r"var-hostname=[^&]*", f"var-hostname={system_name}", current_url)
    page.goto(updated_url, wait_until="domcontentloaded")


@then(parsers.re(r'I should see "(?P<host>[^"]*)" hostname as first search result$'))
def step_should_see_hostname_as_first_result(page, host: str):
    system_name = get_system_name(host)
    scope = page.locator("xpath=//section").first
    row = scope.locator(
        "xpath=//div[@class='table-responsive']//tr[.//td]"
    ).first
    assert row.get_by_text(system_name).count() > 0, (
        f"Text '{system_name}' not found in first result row"
    )


@when(parsers.re(r'I enter "(?P<search_text>[^"]*)" as the left menu search field$'))
def step_enter_left_menu_search(page, search_text: str):
    enter_text_in_field(page, search_text, "nav-search")


@then("I should see left menu empty")
def step_should_see_left_menu_empty(page):
    assert page.locator(
        "xpath=//*[contains(@class, 'level1')]/*/*[contains(@class, 'nodeLink')]"
    ).count() == 0, "The left menu is not empty."


@then(parsers.re(
    r'I should see the text "(?P<text>.*?)" in the (?P<field>Operating System|Architecture|Channel Label) field'
))
def step_should_see_text_in_field(page, text: str, field: str):
    # Note: the Ruby version's logic appears inverted (has_field? args are swapped).
    # Porting faithfully.
    assert page.locator(
        f'[placeholder="{text}"], [value="{text}"]'
    ).count() > 0 or check_text(page, text, timeout=3)


@then(parsers.re(r'I should see the correct timestamp for task "(?P<task_name>[^"]*)"'))
def step_should_see_correct_timestamp(page, task_name: str):
    import datetime
    page.evaluate("window.stop()")
    now = datetime.datetime.now()
    rows = page.locator("xpath=//table[@class='table table-responsive']//tr").all()
    for row in rows:
        if task_name not in row.inner_text():
            continue
        cells = page.locator("xpath=//table[@class='table table-responsive']//td").all()
        for td in cells:
            text = td.inner_text()
            if re.search(r'\d{2}:\d{2}', text):
                try:
                    ts = datetime.datetime.strptime(text.strip(), "%H:%M")
                    ts = ts.replace(year=now.year, month=now.month, day=now.day)
                    diff = abs((ts - now).total_seconds())
                    assert diff <= 5, f"Timestamp {text} is not within 5s of now"
                except ValueError:
                    pass


@when(parsers.re(r'I visit the grafana dashboards of this "(?P<host>[^"]*)"'))
def step_visit_grafana_dashboards(page, host: str):
    node = get_target(host)
    page.goto(f"http://{node.public_ip}:3000/dashboards", wait_until="domcontentloaded")


# ---------------------------------------------------------------------------
# Password Policy navigation steps
# ---------------------------------------------------------------------------

@when(parsers.re(r'I set the minimum password length to "(?P<min_length>[^"]*)"$'))
def step_set_min_password_length(page, min_length: str):
    page.locator("#minLength").fill(min_length)


@when(parsers.re(r'I set the maximum password length to "(?P<max_length>[^"]*)"$'))
def step_set_max_password_length(page, max_length: str):
    page.locator("#maxLength").fill(max_length)


@when(parsers.re(r'I set the special characters list to "(?P<characters_list>[^"]*)"$'))
def step_set_special_characters(page, characters_list: str):
    page.locator("#specialChars").fill(characters_list)


@when(parsers.re(
    r'I set the maximum allowed occurrence of any character to "(?P<max_occurence>[^"]*)"$'
))
def step_set_max_char_occurrence(page, max_occurence: str):
    page.locator("#maxCharacterOccurrence").fill(max_occurence)


_RESTRICTION_MAP = {
    "Require Digits":                  "digitFlag",
    "Require Lowercase Characters":    "lowerCharFlag",
    "Require Uppercase Characters":    "upperCharFlag",
    "Require Special Characters":      "specialCharFlag",
    "Restrict Characters Occurrences": "restrictedOccurrenceFlag",
    "Restrict Consecutive Characters": "consecutiveCharsFlag",
}


@when(parsers.re(r'I (?P<action>enable|disable) the following restrictions:$'))
def step_enable_disable_restrictions(page, action: str, datatable):
    toggle = "check" if action == "enable" else "uncheck"
    for row in datatable:
        restriction = row[0]
        checkbox_id = _RESTRICTION_MAP.get(restriction)
        if not checkbox_id:
            raise ValueError(f"Unknown restriction: {restriction}")
        toggle_checkbox(page, toggle, checkbox_id)


@then(parsers.re(r'the following restrictions should be (?P<expected_state>enabled|disabled):$'))
def step_restrictions_should_be(page, expected_state: str, datatable):
    expected_checkbox_state = "checked" if expected_state == "enabled" else "unchecked"
    for row in datatable:
        restriction = row[0]
        checkbox_id = _RESTRICTION_MAP.get(restriction)
        if not checkbox_id:
            raise ValueError(f"Unknown restriction: {restriction}")
        actual = checkbox_state(page, checkbox_id)
        assert actual == expected_checkbox_state, (
            f"Expected '{restriction}' to be {expected_checkbox_state}, but was {actual}"
        )


# ---------------------------------------------------------------------------
# Check in list by text (generic)
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check "(?P<text>[^"]*)" in the list$'))
def step_check_text_in_list(page, text: str):
    toggle_checkbox_in_list(page, "check", text)
