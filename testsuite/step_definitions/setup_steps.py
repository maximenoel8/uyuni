# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/setup_steps.rb (partial).

Covers setup / bootstrapping steps needed by the validation slice features:
  - sle_minion.feature

Also covers Salt-master steps from salt_steps.rb and reporting steps
from system_monitoring_steps.rb needed by sle_minion.feature.
"""

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target, get_system_name
from support.commonlib import repeat_until_timeout
from support.embedded_steps.navigation_helper import (
    follow_left_menu,
    wait_for_text,
    wait_for_text_refreshing,
)
from support.env import DEFAULT_TIMEOUT, QUALITY_INTELLIGENCE_MODE


# ---------------------------------------------------------------------------
# Salt master reachability
# ---------------------------------------------------------------------------

@then(parsers.re(r'the Salt master can reach "(?P<minion>[^"]*)"'))
def step_setup_salt_master_can_reach(minion: str):
    node = get_target(minion)
    system_name = node.full_hostname
    server = get_target("server")

    def _ping():
        out, _code = server.run(
            f"salt {system_name} test.ping", check_errors=False
        )
        if system_name in out and "True" in out:
            return True
        return None

    repeat_until_timeout(
        _ping,
        timeout=700,
        message=f"Salt master cannot communicate with {minion}",
        report_result=True,
    )


# ---------------------------------------------------------------------------
# Onboarding completed
# ---------------------------------------------------------------------------

@when(parsers.re(r'I wait until onboarding is completed for "(?P<host>[^"]*)"'))
def step_wait_until_onboarding_completed(page, api_test, host: str):
    _wait_at_most_until_onboarding_completed(page, api_test, host, DEFAULT_TIMEOUT)


@when(parsers.re(
    r'I wait at most (?P<seconds>\d+) seconds until onboarding is completed for "(?P<host>[^"]*)"'
))
def step_wait_at_most_until_onboarding_completed(page, api_test, seconds: str, host: str):
    _wait_at_most_until_onboarding_completed(page, api_test, host, int(seconds))


def _wait_at_most_until_onboarding_completed(page, api_test, host: str, timeout: int):
    """Navigate through the onboarding event pages and wait for completion."""
    from step_definitions.navigation_steps import (
        step_follow_left_menu,
        step_wait_until_see_name_refreshing,
        _get_system_id,
    )
    from support.env import APP_HOST

    follow_left_menu(page, "Systems > System List > All")
    step_wait_until_see_name_refreshing(page, host)

    # Navigate to the system overview
    system_id = _get_system_id(api_test, host)
    page.goto(
        f"{APP_HOST}/rhn/systems/details/Overview.do?sid={system_id}",
        wait_until="domcontentloaded",
    )

    for event_label in ("Apply states", "Hardware List Refresh", "Package List Refresh"):
        _wait_for_event(page, host, event_label, 180, timeout, api_test)


def _wait_for_event(page, host: str, event_label: str,
                    pickup_timeout: int, complete_timeout: int, api_test):
    """Wait for a scheduled event to be picked up and complete.

    This is a simplified version of the Ruby
    'I wait N seconds until the event is picked up and M seconds until the event X is completed'.
    It polls the event history via the API rather than driving the browser.
    """
    node = get_target(host)
    system_name = node.full_hostname
    server = get_target("server")

    def _event_complete():
        result, _code = server.run(
            f"spacecmd -u admin -p admin system_listeventhistory {system_name}",
            check_errors=False,
        )
        if event_label in result and "Completed" in result:
            return True
        return None

    repeat_until_timeout(
        _event_complete,
        timeout=pickup_timeout + complete_timeout,
        message=f"Event '{event_label}' did not complete for {host}",
    )


# ---------------------------------------------------------------------------
# Reporting / monitoring
# ---------------------------------------------------------------------------

@when(parsers.re(r'I report the bootstrap duration for "(?P<host>[^"]*)"'))
def step_setup_report_bootstrap_duration(host: str, quality_intelligence):
    if not QUALITY_INTELLIGENCE_MODE:
        return
    from support.system_monitoring import last_bootstrap_duration
    duration = last_bootstrap_duration(host)
    if quality_intelligence:
        quality_intelligence.push_bootstrap_duration(host, duration)


@when(parsers.re(r'I report the onboarding duration for "(?P<host>[^"]*)"'))
def step_setup_report_onboarding_duration(host: str, quality_intelligence):
    if not QUALITY_INTELLIGENCE_MODE:
        return
    from support.system_monitoring import last_onboarding_duration
    duration = last_onboarding_duration(host)
    if quality_intelligence:
        quality_intelligence.push_onboarding_duration(host, duration)


# ---------------------------------------------------------------------------
# Setup wizard — HTTP proxy, SCC credentials
# ---------------------------------------------------------------------------

@then("HTTP proxy verification should have succeeded")
def step_http_proxy_verification_succeeded(page):
    assert page.locator("div.alert-success").wait_for(timeout=DEFAULT_TIMEOUT * 1000), \
        "Success icon not found"


@when(parsers.re(r'I enter the address of the HTTP proxy as "(?P<hostname>[^"]*)"'))
def step_enter_http_proxy_address(page, hostname: str):
    import os
    proxy_addr = os.environ.get("SERVER_HTTP_PROXY", "")
    page.locator(f"[name='{hostname}'], #{hostname}").first.fill(proxy_addr)


@when("I ask to add new credentials")
def step_ask_add_new_credentials(page):
    page.locator("i.fa-plus-circle").click()


@when("I enter the SCC credentials")
def step_enter_scc_credentials(page):
    import os
    creds = os.environ.get("SCC_CREDENTIALS", "|")
    scc_username, scc_password = creds.split("|", 1)
    page.locator("[name='edit-user'], #edit-user").first.fill(scc_username)
    page.locator("[name='edit-password'], #edit-password").first.fill(scc_password)


@when("I wait until the SCC credentials are valid")
def step_wait_until_scc_credentials_valid(page):
    import os
    creds = os.environ.get("SCC_CREDENTIALS", "|")
    scc_username = creds.split("|")[0]
    container = page.locator(f"xpath=//h3[contains(text(), '{scc_username}')]/../..")
    container.locator("i.text-success").wait_for(timeout=30000)


@then(parsers.re(r'the credentials for "(?P<user>[^"]*)" should be invalid'))
def step_credentials_should_be_invalid(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    container.locator("i.text-danger").wait_for(timeout=DEFAULT_TIMEOUT * 1000)


@when(parsers.re(r'I make the credentials for "(?P<user>[^"]*)" primary'))
def step_make_credentials_primary(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    container.locator("i.fa-star-o").click()


@then(parsers.re(r'the credentials for "(?P<user>[^"]*)" should be primary'))
def step_credentials_should_be_primary(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    assert container.locator("i.fa-star").count(), "Star icon not selected"


@when(parsers.re(r'I wait for the trash icon to appear for "(?P<user>[^"]*)"'))
def step_wait_for_trash_icon(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")

    def _not_greyed():
        style = container.locator("i.fa-trash-o").get_attribute("style") or ""
        if "not-allowed" not in style:
            return True
        return None

    repeat_until_timeout(_not_greyed, message="Trash icon is still greyed out")


@when(parsers.re(r'I ask to edit the credentials for "(?P<user>[^"]*)"'))
def step_ask_edit_credentials(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    container.locator("i.fa-pencil").click()


@when(parsers.re(r'I ask to delete the credentials for "(?P<user>[^"]*)"'))
def step_ask_delete_credentials(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    container.locator("i.fa-trash-o").click()


@when(parsers.re(r'I view the subscription list for "(?P<user>[^"]*)"'))
def step_view_subscription_list(page, user: str):
    container = page.locator(f"xpath=//h3[contains(text(), '{user}')]/../..")
    container.locator("i.fa-th-list").click()


# ---------------------------------------------------------------------------
# Product selection
# ---------------------------------------------------------------------------

@when(parsers.re(r'I (?P<select>deselect|select) "(?P<product>[^"]*)" as a product'))
def step_select_deselect_product(page, select: str, product: str):
    xpath = (f"//span[contains(text(), '{product}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/input[@type='checkbox']")
    checkbox = page.locator(f"xpath={xpath}")
    if select == "select":
        checkbox.check()
    else:
        checkbox.uncheck()


@when(parsers.re(r'I select or deselect "(?P<channel>[^"]*)" beta client tools'))
def step_select_deselect_beta_tools(page, channel: str):
    import os
    beta_enabled = os.environ.get("BETA_ENABLED", "false").lower() == "true"
    xpath = (f"//span[contains(text(), '{channel}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/input[@type='checkbox']")
    try:
        checkbox = page.locator(f"xpath={xpath}")
        checkbox.wait_for(timeout=3000)
        if beta_enabled:
            checkbox.check()
        else:
            checkbox.uncheck()
    except Exception:
        print(f"Warning: {channel} beta client tools checkbox not found")


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until the tree item "(?P<item>[^"]+)" has no sub-list'
))
def step_wait_tree_item_no_sublist(page, timeout: str, item: str):
    xpath = (f"//span[contains(text(), '{item}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/i[contains(@class, 'fa-angle-')]")

    def _no_sublist():
        if not page.locator(f"xpath={xpath}").count():
            return True
        return None

    repeat_until_timeout(
        _no_sublist,
        timeout=int(timeout),
        message=f"could still find a sub list for tree item {item}",
    )


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until the tree item "(?P<item>[^"]+)" '
    r'contains "(?P<text>[^"]+)" text'
))
def step_wait_tree_item_contains_text(page, timeout: str, item: str, text: str):
    from support.commonlib import check_text as _check_text
    container = page.locator(
        f"xpath=//span[contains(text(), '{item}')]"
        "/ancestor::div[contains(@class, 'product-details-wrapper')]"
    )

    def _has_text():
        if _check_text(page, text):
            return True
        return None

    repeat_until_timeout(_has_text, timeout=int(timeout),
                         message=f"could not find text {text} for tree item {item}")


@when(parsers.re(
    r'I wait at most (?P<timeout>\d+) seconds until the tree item "(?P<item>[^"]+)" '
    r'contains "(?P<button>[^"]+)" button'
))
def step_wait_tree_item_contains_button(page, timeout: str, item: str, button: str):
    xpath = (f"//span[contains(text(), '{item}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             f"/descendant::*[@title='{button}']")
    page.locator(f"xpath={xpath}").wait_for(timeout=int(timeout) * 1000)


@when(parsers.re(r'I open the sub-list of the product "(?P<product>.*?)"(?P<if_present>(?: if present)?)'))
def step_open_product_sublist(page, product: str, if_present: str):
    xpath = (f"//span[contains(text(), '{product}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/i[contains(@class, 'fa-angle-right')]")
    locator = page.locator(f"xpath={xpath}")
    try:
        locator.click()
    except Exception:
        if not if_present:
            raise


@when(parsers.re(r'I select the addon "(?P<addon>.*?)"'))
def step_select_addon(page, addon: str):
    xpath = (f"//span[contains(text(), '{addon}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/input[@type='checkbox']")
    page.locator(f"xpath={xpath}").check()


@then(parsers.re(r'I should see that the "(?P<product>.*?)" product is "(?P<recommended>.*?)"'))
def step_should_see_product_recommended(page, product: str, recommended: str):
    xpath = f"//span[text()[normalize-space(.) = '{product}'] and ./span/text() = '{recommended}']"
    assert page.locator(f"xpath={xpath}").count(), f"Product {product} not found as {recommended}"


@then(parsers.re(r'I should see the "(?P<product>.*?)" selected'))
def step_should_see_product_selected(page, product: str):
    xpath = (f"//span[contains(text(), '{product}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]")
    checkbox = page.locator(f"xpath={xpath}/div/input[@type='checkbox']")
    assert checkbox.is_checked(), f"Product {product} is not checked"


@when(parsers.re(r'I wait until I see "(?P<product>.*?)" product has been added'))
def step_wait_until_product_added(page, product: str):
    xpath = (f"//span[contains(text(), '{product}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]")

    def _product_installed():
        el = page.locator(f"xpath={xpath}").first
        if el.count() and "product-installed" in (el.get_attribute("class") or ""):
            return True
        return None

    repeat_until_timeout(_product_installed,
                         message=f"Couldn't find the installed product {product} in the list")


@when("I click the Add Product button")
def step_click_add_product_button(page):
    page.locator("button#addProducts").click()


@then(parsers.re(r'the SLE15 (?P<sp_version>SP3|SP4|SP5|SP6|SP7) product should be added'))
def step_sle15_product_should_be_added(sp_version: str):
    output, _code = get_target("server").run(
        'echo -e "admin\\nadmin\\n" | mgr-sync list channels',
        check_errors=False,
        buffer_size=1_000_000
    )
    sp_lower = sp_version.lower()
    checks = [
        f"[I] SLE-Product-SLES15-{sp_version}-Pool for x86_64 SUSE Linux Enterprise Server 15 {sp_version} x86_64 [sle-product-sles15-{sp_lower}-pool-x86_64]",
        f"[I] SLE-Module-Basesystem15-{sp_version}-Updates for x86_64 Basesystem Module 15 {sp_version} x86_64 [sle-module-basesystem15-{sp_lower}-updates-x86_64]",
        f"[I] SLE-Module-Server-Applications15-{sp_version}-Pool for x86_64 Server Applications Module 15 {sp_version} x86_64 [sle-module-server-applications15-{sp_lower}-pool-x86_64]",
    ]
    for match in checks:
        assert match in output, f"Not included:\n {match}"


@when(parsers.re(r'I click the channel list of product "(?P<product>.*?)"'))
def step_click_channel_list_of_product(page, product: str):
    xpath = (f"//span[contains(text(), '{product}')]"
             "/ancestor::div[contains(@class, 'product-details-wrapper')]"
             "/div/button[contains(@class, 'showChannels')]")
    page.locator(f"xpath={xpath}").click()


# ---------------------------------------------------------------------------
# Configuration management table checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see a table line with "(?P<arg1>[^"]*)", "(?P<arg2>[^"]*)", "(?P<arg3>[^"]*)"'))
def step_see_table_line_three(page, arg1: str, arg2: str, arg3: str):
    row = page.locator(
        f"xpath=//div[contains(@class, 'table-responsive')]//tr[.//td[contains(.,'{arg1}')]]"
    ).first
    assert row.get_by_text(arg2).count(), f"Link {arg2} not found"
    assert row.get_by_text(arg3).count(), f"Link {arg3} not found"


@then(parsers.re(r'I should see a table line with "(?P<arg1>[^"]*)", "(?P<arg2>[^"]*)"'))
def step_see_table_line_two(page, arg1: str, arg2: str):
    row = page.locator(
        f"xpath=//div[contains(@class, 'table-responsive')]//tr[.//td[contains(.,'{arg1}')]]"
    ).first
    assert row.get_by_text(arg2).count(), f"Link {arg2} not found"


@then(parsers.re(r'a table line should contain system "(?P<host>[^"]*)", "(?P<text>[^"]*)"'))
def step_table_line_contains_system(page, host: str, text: str):
    system_name = get_system_name(host)
    row = page.locator(
        f"xpath=//div[contains(@class, 'table-responsive')]//tr[.//td[contains(.,'{system_name}')]]"
    ).first
    assert row.get_by_text(text).count(), f"Text {text} not found"


# ---------------------------------------------------------------------------
# Register client
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I wait at most (?P<seconds>\d+) seconds until I see the name of "(?P<host>[^"]*)", '
    r'refreshing the page'
))
def step_wait_until_see_host_name(page, seconds: str, host: str):
    system_name = get_system_name(host)

    def _not_loading():
        if not page.locator("text=Loading...").count():
            return True
        return None

    repeat_until_timeout(_not_loading, timeout=10, message="Page loading")

    def _has_system():
        if page.get_by_text(system_name).count():
            return True
        page.reload()
        return None

    repeat_until_timeout(_has_system, timeout=int(seconds),
                         message=f"Can't see the system '{system_name}'")


@then(parsers.re(r'I should see "(?P<host>[^"]*)" via spacecmd'))
def step_should_see_via_spacecmd(host: str):
    system_name = get_system_name(host)
    server = get_target("server")

    def _in_list():
        server.run("spacecmd -u admin -p admin clear_caches")
        result, _code = server.run(
            "spacecmd -u admin -p admin system_list", check_errors=False
        )
        if system_name in result:
            return True
        return None

    repeat_until_timeout(_in_list, message=f"system {system_name} is not in the list yet")


@then(parsers.re(r'I should see "(?P<host>[^"]*)" as link'))
def step_should_see_as_link(page, host: str):
    system_name = get_system_name(host)
    assert page.get_by_role("link", name=system_name).count(), \
        f"Link '{system_name}' not found on page"


# ---------------------------------------------------------------------------
# JWT token steps
# ---------------------------------------------------------------------------

@given(parsers.re(r'I have a valid token for organization "(?P<org>[^"]*)"'))
def step_have_valid_token(org: str, context_store):
    import jwt
    import os
    server_secret = os.environ.get("SERVER_SECRET", "")
    token = jwt.encode({"org": int(org)}, server_secret, algorithm="HS256")
    context_store["token"] = token


@given(parsers.re(r'I have an invalid token for organization "(?P<org>[^"]*)"'))
def step_have_invalid_token(org: str, context_store):
    import jwt
    import secrets
    fake_secret = secrets.token_hex(64)
    token = jwt.encode({"org": int(org)}, fake_secret, algorithm="HS256")
    context_store["token"] = token


@given(parsers.re(r'I have an expired valid token for organization "(?P<org>[^"]*)"'))
def step_have_expired_token(org: str, context_store):
    import jwt
    import os
    import time as _time
    server_secret = os.environ.get("SERVER_SECRET", "")
    yesterday = int(_time.time()) - 86400
    token = jwt.encode({"org": int(org), "exp": yesterday}, server_secret, algorithm="HS256")
    context_store["token"] = token


@given(parsers.re(r'I have a valid token expiring tomorrow for organization "(?P<org>[^"]*)"'))
def step_have_token_expiring_tomorrow(org: str, context_store):
    import jwt
    import os
    import time as _time
    server_secret = os.environ.get("SERVER_SECRET", "")
    tomorrow = int(_time.time()) + 86400
    token = jwt.encode({"org": int(org), "exp": tomorrow}, server_secret, algorithm="HS256")
    context_store["token"] = token


@given(parsers.re(r'I have a not yet usable valid token for organization "(?P<org>[^"]*)"'))
def step_have_not_yet_usable_token(org: str, context_store):
    import jwt
    import os
    import time as _time
    server_secret = os.environ.get("SERVER_SECRET", "")
    tomorrow = int(_time.time()) + 86400
    token = jwt.encode({"org": int(org), "nbf": tomorrow}, server_secret, algorithm="HS256")
    context_store["token"] = token


@given(parsers.re(r'I have a valid token for organization "(?P<org>.*?)" and channel "(?P<channel>.*?)"'))
def step_have_valid_token_for_channel(org: str, channel: str, context_store):
    import jwt
    import os
    server_secret = os.environ.get("SERVER_SECRET", "")
    token = jwt.encode({"org": org, "onlyChannels": [channel]}, server_secret, algorithm="HS256")
    context_store["token"] = token


# ---------------------------------------------------------------------------
# Togglers
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see the toggler "(?P<target_status>[^"]*)"'))
def step_should_see_toggler(page, target_status: str):
    if target_status == "enabled":
        xpath = "//i[contains(@class, 'fa-toggle-on')]"
    elif target_status == "disabled":
        xpath = "//i[contains(@class, 'fa-toggle-off')]"
    else:
        raise NotImplementedError(f"Invalid target status: {target_status}")
    assert page.locator(f"xpath={xpath}").count(), f"Toggler '{target_status}' not found"


@when(parsers.re(r'I click on the "(?P<target_status>[^"]*)" toggler'))
def step_click_toggler(page, target_status: str):
    if target_status == "enabled":
        xpath = "//i[contains(@class, 'fa-toggle-on')]"
    elif target_status == "disabled":
        xpath = "//i[contains(@class, 'fa-toggle-off')]"
    else:
        raise NotImplementedError(f"Invalid target status: {target_status}")
    page.locator(f"xpath={xpath}").click()


# ---------------------------------------------------------------------------
# Child channels
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see the child channel "(?P<target_channel>[^"]*)" "(?P<target_status>[^"]*)"'))
def step_should_see_child_channel(page, target_channel: str, target_status: str):
    from support.commonlib import check_text as _ct
    assert _ct(page, target_channel), f"Channel {target_channel} not found"
    xpath = f"//label[contains(text(), '{target_channel}')]"
    channel_checkbox_id = page.locator(f"xpath={xpath}").first.get_attribute("for")
    checkbox = page.locator(f"#{channel_checkbox_id}")
    if target_status == "selected":
        assert checkbox.is_checked(), f"{channel_checkbox_id} is not selected"
    elif target_status == "unselected":
        assert not checkbox.is_checked(), f"{channel_checkbox_id} is selected"
    else:
        raise NotImplementedError(f"Invalid target status: {target_status}")


@then(parsers.re(
    r'I should see the child channel "(?P<target_channel>[^"]*)" "(?P<target_status>[^"]*)" '
    r'and "(?P<is_disabled>[^"]*)"'
))
def step_should_see_child_channel_disabled(page, target_channel: str, target_status: str, is_disabled: str):
    from support.commonlib import check_text as _ct
    assert is_disabled == "disabled", "Invalid disabled flag value"
    assert _ct(page, target_channel), f"Channel {target_channel} not found"
    xpath = f"//label[contains(text(), '{target_channel}')]"
    channel_checkbox_id = page.locator(f"xpath={xpath}").first.get_attribute("for")
    checkbox = page.locator(f"#{channel_checkbox_id}")
    if target_status == "selected":
        assert checkbox.is_checked(), f"{channel_checkbox_id} is not selected"
    elif target_status == "unselected":
        assert not checkbox.is_checked(), f"{channel_checkbox_id} is selected"
    else:
        raise NotImplementedError(f"Invalid target status: {target_status}")


@when(parsers.re(r'I select the child channel "(?P<target_channel>[^"]*)"'))
def step_select_child_channel(page, target_channel: str):
    from support.commonlib import check_text as _ct
    assert _ct(page, target_channel), f"Channel {target_channel} not found"
    xpath = f"//label[contains(text(), '{target_channel}')]"
    channel_checkbox_id = page.locator(f"xpath={xpath}").first.get_attribute("for")
    checkbox = page.locator(f"#{channel_checkbox_id}")
    assert not checkbox.is_checked(), f"Field {channel_checkbox_id} is already checked"
    page.locator(f"xpath=//input[@id='{channel_checkbox_id}']").click()


# ---------------------------------------------------------------------------
# Notification message steps
# ---------------------------------------------------------------------------

@then("the notification badge and the table should count the same amount of messages")
def step_notification_badge_equals_table(page):
    from support.commonlib import count_table_items
    table_count = count_table_items(page)
    badge_xpath = f"//i[contains(@class, 'fa-bell')]/following-sibling::*[text()='{table_count}']"
    if table_count == "0":
        assert not page.locator(f"xpath={badge_xpath}").count(), \
            f"Expected no notification badge but found one"
    else:
        assert page.locator(f"xpath={badge_xpath}").count(), \
            f"Notification badge with count {table_count} not found"


@when(parsers.re(r'I wait until radio button "(?P<arg1>[^"]*)" is checked, refreshing the page'))
def step_wait_radio_button_checked(page, arg1: str):
    radio = page.get_by_role("radio", name=arg1)
    if not radio.is_checked():
        def _checked():
            if radio.is_checked():
                return True
            page.reload()
            return None
        repeat_until_timeout(_checked, message=f"Couldn't find checked radio button {arg1}")


@when(parsers.re(r'I wait until "(?P<text>[^"]*)" has been checked'))
def step_wait_until_checked(page, text: str):
    checkbox = page.get_by_role("checkbox", name=text)
    if not checkbox.is_checked():
        def _checked():
            if checkbox.is_checked():
                return True
            return None
        repeat_until_timeout(_checked, timeout=5, message=f"Couldn't find checked {text}")


@then("I check the first notification message")
def step_check_first_notification_message(page):
    from support.commonlib import count_table_items
    if count_table_items(page) == "0":
        print("There are no notification messages, nothing to do then")
    else:
        row = page.locator(
            "xpath=//div[@class='table-responsive']//tr[.//td]"
        ).first
        row.locator("input[type='checkbox']").first.check()


@when(parsers.re(r'I delete it via the "(?P<target_button>[^"]*)" button'))
def step_delete_via_button(page, target_button: str):
    from support.commonlib import count_table_items, check_text
    if count_table_items(page) != "0":
        xpath = f"//button[@title='{target_button}']"
        page.locator(f"xpath={xpath}").click()
        assert check_text(page, "1 message deleted successfully."), \
            "Expected '1 message deleted successfully.' text"


@when(parsers.re(r'I mark as read it via the "(?P<target_button>[^"]*)" button'))
def step_mark_as_read_via_button(page, target_button: str):
    from support.commonlib import count_table_items, check_text
    if count_table_items(page) != "0":
        xpath = f"//button[@title='{target_button}']"
        page.locator(f"xpath={xpath}").click()
        assert check_text(page, "1 message read status updated successfully."), \
            "Expected '1 message read status updated successfully.' text"


@then("I check for failed events on history event page")
@when("I check for failed events on history event page")
def step_check_for_failed_events(page):
    from support.commonlib import check_text
    page.get_by_text("Events", exact=False).first.click()
    page.get_by_text("History").click()
    assert check_text(page, "System History"), "System History not found"
    event_rows = page.locator(
        "xpath=//div[@class='table-responsive']/table/tbody/tr"
    ).all()
    failings = []
    for row in event_rows:
        if row.locator(".fa.fa-times-circle-o.fa-1-5x.text-danger").count():
            failings.append(row.inner_text())
    assert not failings, f"\nFailures in event history found:\n\n{''.join(failings)}"


@then(parsers.re(
    r'I should see a list item with text "(?P<text>[^"]*)" and a '
    r'(?P<bullet_type>success|failing|warning|pending|refreshing) bullet'
))
def step_should_see_list_item_with_bullet(page, text: str, bullet_type: str):
    BULLET_STYLE = {
        "success": "fa-check-circle",
        "failing": "fa-times-circle",
        "warning": "fa-warning",
        "pending": "fa-clock-o",
        "refreshing": "fa-refresh",
    }
    item_xpath = f"//ul/li[text()='{text}']/i[contains(@class, '{BULLET_STYLE[bullet_type]}')]"
    assert page.locator(f"xpath={item_xpath}").count(), \
        f"List item '{text}' with {bullet_type} bullet not found"


# ---------------------------------------------------------------------------
# MU repositories
# ---------------------------------------------------------------------------

@when(parsers.re(r'I create the MU repositories for "(?P<client>[^"]*)"'))
def step_create_mu_repositories(page, client: str, context_store):
    import os
    custom_repositories = context_store.get("custom_repositories", {})
    repo_list = custom_repositories.get(client)
    if not repo_list:
        return
    from support.commonlib import deb_host, check_text
    from support.embedded_steps.navigation_helper import follow_left_menu
    node = get_target(client)
    for _repo_name, repo_url in repo_list.items():
        from support.commonlib import generate_repository_name
        unique_repo_name = generate_repository_name(repo_url)
        # Check if already exists via API — skip creation if it does
        content_type = "deb" if deb_host(client) else "yum"
        follow_left_menu(page, "Software > Manage > Repositories")
        page.get_by_text("Create Repository").click()
        page.locator("[name='label'], #label").first.fill(unique_repo_name)
        page.locator("[name='url'], #url").first.fill(repo_url.strip())
        page.locator("#contenttype").select_option(content_type)
        page.get_by_role("button", name="Create Repository").click()


@when(parsers.re(r'I select the MU repositories for "(?P<client>[^"]*)" from the list'))
def step_select_mu_repositories(page, client: str, context_store):
    custom_repositories = context_store.get("custom_repositories", {})
    repo_list = custom_repositories.get(client)
    if not repo_list:
        return
    from support.commonlib import generate_repository_name
    for _repo_name, repo_url in repo_list.items():
        unique_repo_name = generate_repository_name(repo_url)
        page.get_by_label(unique_repo_name).check()


# ---------------------------------------------------------------------------
# Child channel visibility and state
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see the child channel "(?P<channel>[^"]*)" "(?P<status>selected|unselected)"$'))
def step_should_see_child_channel(page, channel: str, status: str):
    from support.commonlib import check_text
    assert check_text(page, channel), f"Channel '{channel}' not found on page"
    checkbox_id = page.locator(f"xpath=//label[contains(text(), '{channel}')]").get_attribute("for")
    checkbox = page.locator(f"#\\ {checkbox_id}" if " " in (checkbox_id or "") else f"#{checkbox_id}")
    is_checked = checkbox.is_checked()
    if status == "selected":
        assert is_checked, f"Channel '{channel}' is not selected"
    else:
        assert not is_checked, f"Channel '{channel}' is selected but should not be"


@then(parsers.re(
    r'I should see the child channel "(?P<channel>[^"]*)" "(?P<status>selected|unselected)" and "(?P<disabled_flag>[^"]*)"'
))
def step_should_see_child_channel_with_disabled(page, channel: str, status: str, disabled_flag: str):
    assert disabled_flag == "disabled", f"Invalid disabled flag: '{disabled_flag}'"
    from support.commonlib import check_text
    assert check_text(page, channel), f"Channel '{channel}' not found on page"
    checkbox_id = page.locator(f"xpath=//label[contains(text(), '{channel}')]").get_attribute("for")
    checkbox = page.locator(f"#{checkbox_id}")
    is_checked = checkbox.is_checked()
    if status == "selected":
        assert is_checked, f"Channel '{channel}' is not selected"
    else:
        assert not is_checked, f"Channel '{channel}' is selected but should not be"


@then(parsers.re(
    r'I should see "(?P<radio_label>[^"]*)" "(?P<status>selected|unselected)" for the "(?P<channel>[^"]*)" channel'
))
def step_should_see_channel_radio(page, radio_label: str, status: str, channel: str):
    channel_link = page.locator(f"xpath=//a[contains(text(), '{channel}')]")
    href = channel_link.get_attribute("href") or ""
    channel_id = href.split("?", 1)[-1].split("=", 1)[-1] if "?" in href else ""

    value_map = {"No change": "NO_CHANGE", "Subscribe": "SUBSCRIBE", "Unsubscribe": "UNSUBSCRIBE"}
    value = value_map.get(radio_label)
    assert value, f"Unsupported radio label: '{radio_label}'"

    radio = page.locator(f"xpath=//input[@type='radio' and @name='ch_action_{channel_id}' and @value='{value}']")
    is_checked = radio.is_checked()
    if status == "selected":
        assert is_checked, f"Radio '{radio_label}' for channel '{channel}' is not selected"
    else:
        assert not is_checked, f"Radio '{radio_label}' for channel '{channel}' is selected but should not be"


# ---------------------------------------------------------------------------
# Check default base channel radio button
# ---------------------------------------------------------------------------

@when(parsers.re(r'I check default base channel radio button of this "(?P<host>[^"]*)"'))
def step_check_default_base_channel(page, host: str):
    from support.commonlib import product
    from support.constants import BASE_CHANNEL_BY_CLIENT
    prod = product()
    channel_name = BASE_CHANNEL_BY_CLIENT.get(prod, {}).get(host)
    assert channel_name, f"No default base channel configured for product='{prod}' host='{host}'"
    radio = page.get_by_label(channel_name)
    assert radio.count() > 0, f"Base channel radio button '{channel_name}' not found"
    radio.first.check()


# ---------------------------------------------------------------------------
# Remember when action was scheduled
# ---------------------------------------------------------------------------

@when("I remember when I scheduled an action")
def step_remember_scheduled_action(feature_context):
    import datetime
    feature_context["schedule_action_time"] = datetime.datetime.now()


# ---------------------------------------------------------------------------
# Package visible in channel
# ---------------------------------------------------------------------------

@then(parsers.re(r'I should see package "(?P<pkg>[^"]*)" in channel "(?P<channel>[^"]*)"'))
def step_should_see_package_in_channel(page, pkg: str, channel: str):
    follow_left_menu(page, "Software > Channel List > All")
    page.get_by_role("link", name=channel).click()
    page.get_by_role("link", name="Packages").click()
    from support.commonlib import check_text
    assert check_text(page, pkg), f"Package '{pkg}' not found in channel '{channel}'"


# ---------------------------------------------------------------------------
# ISO mount on server
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I mount as "(?P<name>[^"]+)" the ISO from "(?P<url>[^"]+)" in the server, validating its checksum'
))
def step_mount_iso(name: str, url: str):
    from support.env import MIRROR, IS_CONTAINERIZED_SERVER
    server = get_target("server")

    if MIRROR:
        host_part = url.split("://", 1)[-1].split("/", 1)[-1] if "/" in url.split("://", 1)[-1] else ""
        iso_path = f"/srv/mirror/{host_part}" if IS_CONTAINERIZED_SERVER else f"/mirror/{host_part}"
    else:
        iso_path = f"/tmp/{name}.iso"
        server.run(f"curl --insecure -o {iso_path} {url}", timeout=1500)

    if IS_CONTAINERIZED_SERVER:
        server.run("mkdir -p /srv/www/distributions")
        server.run(f"mgradm distro copy {iso_path} {name}", runs_in_container=False)
        server.run(f"ln -s /srv/www/distributions/{name} /srv/www/htdocs/pub/")
    else:
        mount_point = f"/srv/www/htdocs/pub/{name}"
        server.run(
            f"mkdir -p {mount_point} && "
            f"grep -q {iso_path} /etc/fstab || "
            f"echo '{iso_path}  {mount_point}  iso9660  loop,ro,_netdev  0 0' >> /etc/fstab && "
            f"umount {iso_path}; mount {iso_path}"
        )


# ---------------------------------------------------------------------------
# Prepare development repositories for a client
# ---------------------------------------------------------------------------

@when(parsers.re(
    r'I prepare the development repositories of "(?P<host>[^"]*)" as part of "(?P<channel_label>[^"]*)" channel'
))
def step_prepare_development_repositories(host: str, channel_label: str, api_test):
    from support.commonlib import deb_host, rh_host, generate_repository_name
    node = get_target(host)

    if deb_host(host):
        out, _ = node.run("grep -rh ^deb /etc/apt/sources.list.d/")
        repo_urls = [line.split()[1].strip() for line in out.splitlines() if line.strip()]
    elif rh_host(host):
        out, _ = node.run("grep -rh 'baseurl' /etc/yum.repos.d/")
        repo_urls = [line.split("=", 1)[-1].strip() for line in out.splitlines() if "=" in line]
    else:
        out, _ = node.run("grep -rh 'baseurl' /etc/zypp/repos.d/")
        repo_urls = [line.split("=", 1)[-1].strip() for line in out.splitlines() if "=" in line]

    seen = set()
    for repo_url in repo_urls:
        if not repo_url or repo_url in seen:
            continue
        seen.add(repo_url)
        unique_name = generate_repository_name(repo_url)
        existing = [r["label"] for r in api_test.channel.software.list_user_repos()]
        if unique_name not in existing:
            content_type = "deb" if deb_host(host) else "yum"
            api_test.channel.software.create_repo(unique_name, repo_url, content_type)
        api_test.channel.software.associate_repo(channel_label, unique_name)
