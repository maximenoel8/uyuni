# Copyright (c) 2024-2026 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of features/step_definitions/datepicker_steps.rb.

Covers date and time picker steps for scheduling actions in the SUMA UI.
"""

import time
from datetime import datetime, timedelta

from pytest_bdd import given, when, then, parsers


# ---------------------------------------------------------------------------
# Date picker steps
# ---------------------------------------------------------------------------

@given(parsers.re(r'I pick "(?P<desired_date>[^"]*)" as date'))
def step_pick_date(page, desired_date: str):
    from datetime import date
    value = datetime.strptime(desired_date, "%Y-%m-%d").date()
    date_input = page.locator('input[data-testid="date-picker"]')
    date_input.click()
    date_input.press("Control+a")
    date_input.press("Backspace")
    date_input.type(value.strftime("%Y-%m-%d"))
    date_input.press("Enter")


@then(parsers.re(r'the date field should be set to "(?P<expected_date>[^"]*)"'))
def step_date_field_should_be_set(page, expected_date: str):
    value = datetime.strptime(expected_date, "%Y-%m-%d").date()
    day_compat = page.locator("input#date_day")
    month_compat = page.locator("input#date_month")
    year_compat = page.locator("input#date_year")

    assert int(day_compat.input_value()) == value.day, "Day field mismatch"
    # month field is 0-indexed in JS but 1-indexed in Python
    assert int(month_compat.input_value()) + 1 == value.month, "Month field mismatch"
    assert int(year_compat.input_value()) == value.year, "Year field mismatch"


@given("I open the date picker")
def step_open_date_picker(page):
    page.locator('input[data-testid="date-picker"]').click()


@then("the date picker should be closed")
def step_date_picker_should_be_closed(page):
    assert not page.locator(".date-time-picker-popup").count(), "The date picker is not closed"


@then("the date picker title should be the current month and year")
def step_date_picker_title_current_month_year(page):
    now = datetime.now().strftime("%B %Y")
    step_date_picker_title_should_be(page, now)


@then(parsers.re(r'the date picker title should be "(?P<arg1>[^"]*)"'))
def step_date_picker_title_should_be(page, arg1: str):
    if not page.locator(".date-time-picker-popup").count():
        page.locator('input[data-testid="date-picker"]').click()
    switch = page.locator(".date-time-picker-popup .react-datepicker__current-month")
    assert switch.inner_text() == arg1 or arg1 in switch.inner_text(), \
        f"The date picker title '{switch.inner_text()}' does not contain '{arg1}'"


# ---------------------------------------------------------------------------
# Time picker steps
# ---------------------------------------------------------------------------

@given(parsers.re(r'I pick "(?P<desired_time>[^"]*)" as time'))
def step_pick_time(page, desired_time: str):
    page.locator('input[data-testid="time-picker"]').click()
    timepicker = page.locator("ul.react-datepicker__time-list").first
    timepicker.locator(f"xpath=//*[normalize-space(text())='{desired_time}']").click()


@when(parsers.re(r'I pick "(?P<desired_time>[^"]*)" as time from "(?P<element_id>[^"]*)"'))
def step_pick_time_from_element(page, desired_time: str, element_id: str):
    page.locator(f'input[data-testid="time-picker"]#{element_id}').click()
    timepicker = page.locator("ul.react-datepicker__time-list").first
    timepicker.locator(f"xpath=//*[normalize-space(text())='{desired_time}']").click()


@when(parsers.re(r'I pick (?P<arg1>\d+) minutes from now as schedule time'))
def step_pick_minutes_from_now(page, arg1: str):
    from support.commonlib import get_future_time
    action_time = get_future_time(int(arg1))
    page.locator("xpath=//*[@id='date_timepicker_widget_input']").wait_for(timeout=2000)
    page.locator("#date_timepicker_widget_input").fill(action_time)


@when(parsers.re(r'I schedule action to (?P<minutes>\d+) minutes from now'))
def step_schedule_action_minutes_from_now(page, minutes: str):
    future = datetime.now() + timedelta(minutes=int(minutes), seconds=59)
    action_date = future.strftime("%Y-%m-%d")
    action_time = future.strftime("%H:%M")

    date_input = page.locator('input[data-testid="date-picker"]')
    date_input.click()
    date_input.press("Control+a")
    date_input.press("Backspace")
    date_input.type(action_date)
    date_input.press("Enter")

    time_input = page.locator('input[data-testid="time-picker"]')
    time_input.click()
    time_input.press("Control+a")
    time_input.press("Backspace")
    time_input.type(action_time)
    time_input.press("Enter")


@then(parsers.re(r'the time field should be set to "(?P<expected_time>[^"]*)"'))
def step_time_field_should_be_set(page, expected_time: str):
    h, m = [int(x) for x in expected_time.strip().split(":")]
    h_compat = page.locator("input#date_hour")
    m_compat = page.locator("input#date_minute")
    ampm_compat = page.locator("input#date_am_pm")

    assert int(h_compat.input_value()) == h % 12, "Invalid hidden hour"
    assert int(m_compat.input_value()) == m, "Invalid hidden minute"
    assert int(ampm_compat.input_value()) == (1 if h >= 12 else 0), "Invalid hidden AM/PM"
