# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/lock_packages_on_client.rb.

Covers steps for locking and unlocking packages on a system.
"""

import time

from pytest_bdd import given, when, then, parsers

from support.remote_nodes_env import get_target
from support.commonlib import check_text, repeat_until_timeout


# ---------------------------------------------------------------------------
# SSH package lock checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'"(?P<pkg>.*?)" should be (?P<action>locked|unlocked) on "(?P<system>.*?)"'))
def step_package_locked_or_unlocked(pkg: str, action: str, system: str):
    node = get_target(system)
    command = f"zypper locks --solvables | grep {pkg}"
    if action == "locked":
        def _is_locked():
            _out, code = node.run(command, check_errors=False, timeout=10)
            if code == 0:
                return True
            time.sleep(2)
            return None

        repeat_until_timeout(_is_locked, timeout=30,
                             message=f"Package {pkg} is not locked on {system}")
    else:
        _out, code = node.run(command, check_errors=False, timeout=600)
        assert code != 0, f"Package {pkg} is still locked on {system}"


# ---------------------------------------------------------------------------
# Browser UI package lock checks
# ---------------------------------------------------------------------------

@then(parsers.re(r'package "(?P<pkg>.*?)" is reported as locked'))
def step_package_reported_as_locked(page, pkg: str):
    assert page.locator(f"xpath=(//a[text()='{pkg}'])[1]").count(), f"Package {pkg} not found"
    locked_pkgs = page.locator("xpath=//i[@class='fa fa-lock']/../a").all()
    assert locked_pkgs, "No packages locked"
    assert any(a.inner_text().startswith(pkg) for a in locked_pkgs), \
        f"Package {pkg} not found as locked"


@then(parsers.re(r'package "(?P<pkg>.*?)" is reported as unlocked'))
def step_package_reported_as_unlocked(page, pkg: str):
    assert page.locator(f"xpath=(//a[text()='{pkg}'])[1]").count(), f"Package {pkg} not found"
    locked_pkgs = page.locator("xpath=//i[@class='fa fa-lock']/../a").all()
    for a in locked_pkgs:
        assert not a.inner_text().startswith(pkg), f"Package {pkg} found as locked"


@then(parsers.re(r'the package scheduled is "(?P<pkg>.*?)"'))
def step_package_scheduled_is(page, pkg: str):
    match = page.locator("xpath=//li[@class='list-group-item']//li").first
    assert match.count(), "List of packages not found"
    assert match.inner_text().startswith(pkg), f"Package {pkg} not found"


@then(parsers.re(r'the action status is "(?P<status>.*?)"'))
def step_action_status_is(page, status: str):
    assert check_text(page, f"This action's status is: {status}"), \
        f"Action status '{status}' not found"


@then(parsers.re(r'package "(?P<pkg>.*?)" is reported as pending to be locked'))
def step_package_pending_to_be_locked(page, pkg: str):
    xpath = (
        f"//td[a[text()='{pkg}'] and "
        "i[@class='fa fa-clock-o'] and "
        "span[@class='label label-info' and contains(text(), 'Locking...')]]"
    )
    assert page.locator(f"xpath={xpath}").count(), f"Package {pkg} not pending to be locked"


@then(parsers.re(r'package "(?P<pkg>.*?)" is reported as pending to be unlocked'))
def step_package_pending_to_be_unlocked(page, pkg: str):
    xpath = (
        f"//td[a[text()='{pkg}'] and "
        "i[@class='fa fa-clock-o'] and "
        "span[@class='label label-info' and contains(text(), 'Unlocking...')]]"
    )
    assert page.locator(f"xpath={xpath}").count(), f"Package {pkg} not pending to be unlocked"


@then(parsers.re(r'package "(?P<pkg>.*?)" cannot be selected'))
def step_package_cannot_be_selected(page, pkg: str):
    xpath = (
        f"//tr[td[input[@type='checkbox' and @disabled]] and "
        f"td[a[text()='{pkg}'] and "
        "i[@class='fa fa-clock-o'] and "
        "span[@class='label label-info']]]"
    )
    assert page.locator(f"xpath={xpath}").count(), f"Package {pkg} can still be selected"


@then(parsers.re(r'only packages "(?P<pkgs>.*?)" are reported as pending to be unlocked'))
def step_only_packages_pending_to_be_unlocked(page, pkgs: str):
    pkg_list = [p.strip() for p in pkgs.split(",")]

    for pkg in pkg_list:
        xpath = (
            f"//td[a[text()='{pkg}'] and "
            "i[@class='fa fa-clock-o'] and "
            "span[@class='label label-info' and contains(text(), 'Unlocking...')]]"
        )
        assert page.locator(f"xpath={xpath}").count(), f"Package {pkg} not pending to be unlocked"

    # Ensure no other packages are pending to be unlocked
    all_unlocking_xpath = (
        "//td[i[@class='fa fa-clock-o'] and "
        "span[@class='label label-info' and contains(text(), 'Unlocking...')]]"
    )
    matches = page.locator(f"xpath={all_unlocking_xpath}").all()
    assert len(matches) == len(pkg_list), \
        f"Matches count {len(matches)} is different than packages count {len(pkg_list)}"
