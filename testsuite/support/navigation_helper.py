# Copyright (c) 2025 SUSE LLC.
# Licensed under the terms of the MIT license.

"""Navigation helper functions ported from navigation_step_helper.rb."""


def toggle_checkbox(page, action: str, element_id: str):
    """Check or uncheck a checkbox by its HTML id.

    Compares the current state with the desired state and clicks only if
    they differ, matching the Ruby implementation behaviour.

    Args:
        page: Playwright page (or locatable scope).
        action: 'check' or 'uncheck'.
        element_id: The HTML id attribute of the checkbox element.
    """
    cb = page.locator(f"#{element_id}")
    desired = action == "check"
    if cb.is_checked() != desired:
        cb.click()


def checkbox_state(page, element_id: str) -> str:
    """Return 'checked' or 'unchecked' for a checkbox by id.

    Args:
        page: Playwright page (or locatable scope).
        element_id: The HTML id attribute of the checkbox element.

    Returns:
        'checked' if the checkbox is selected, 'unchecked' otherwise.
    """
    cb = page.locator(f"#{element_id}")
    return "checked" if cb.is_checked() else "unchecked"


def toggle_checkbox_in_list(scope_or_page, action: str, text: str):
    """Toggle a checkbox in a table row containing the given text.

    Args:
        scope_or_page: Playwright page or locator scope.
        action: 'check' or 'uncheck'.
        text: The text that must appear somewhere in the target row.

    Raises:
        RuntimeError: If no matching checkbox element is found.
    """
    xpath = (
        f'xpath=//table/tbody/tr[.//td[contains(.,"{text}")]]'
        f'//input[@type="checkbox"]'
    )
    cb = scope_or_page.locator(xpath).first
    if cb.count() == 0:
        raise RuntimeError(f"xpath: {xpath} not found")
    if action == "check":
        cb.check()
    else:
        cb.uncheck()


def _latest_package(packages: list) -> str:
    """Return the lexicographically latest package version string.

    This mirrors the Ruby ``latest_package`` helper used inside
    ``toggle_checkbox_in_package_list``.

    Args:
        packages: List of package version strings.

    Returns:
        The package string that sorts last.
    """
    return max(packages) if packages else ""


def toggle_checkbox_in_package_list(scope_or_page, action: str, text: str,
                                    last_version: bool = False):
    """Toggle a checkbox in a package list row, optionally targeting the last version.

    When *last_version* is True the function attempts to locate the row whose
    sortedCol cell contains the latest package name (matching the Ruby logic).
    On any failure it falls back to a plain text-match via
    :func:`toggle_checkbox_in_list`.

    Args:
        scope_or_page: Playwright page or locator scope.
        action: 'check' or 'uncheck'.
        text: The text that must appear somewhere in the target row.
        last_version: When True, target the row with the latest package version.
    """
    if last_version:
        try:
            link_elements = scope_or_page.locator(
                "xpath=//table/tbody/tr/td[contains(@class,'sortedCol')]/a"
            ).all()
            packages = [el.inner_text() for el in link_elements]
            latest = _latest_package(packages)

            xpath = (
                f'xpath=//table/tbody/tr/td[contains(@class,"sortedCol")]'
                f'/a[text()="{latest}"]/ancestor::tr//input[@type="checkbox"]'
            )
            cb = scope_or_page.locator(xpath).first
            if action == "check":
                cb.check()
            else:
                cb.uncheck()
        except Exception as exc:
            import warnings
            warnings.warn(f"[toggle_checkbox_in_package_list] fallback to text match: {exc}")
            toggle_checkbox_in_list(scope_or_page, action, text)
    else:
        toggle_checkbox_in_list(scope_or_page, action, text)


def filter_by_package_name(page, package_name: str):
    """Enter a package name into the filter input and submit.

    Args:
        page: Playwright page.
        package_name: The package name to filter by.

    Raises:
        ValueError: If *package_name* is empty.
    """
    if not package_name:
        raise ValueError("Package name is not set")

    input_field = page.locator("input[placeholder='Filter by Package Name: ']").first
    input_field.fill(package_name)
    input_field.press("Enter")
