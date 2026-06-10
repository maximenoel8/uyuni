from support.env import APP_HOST
from support.commonlib import (
    wait_for_ajax, click_link_and_wait, click_button_and_wait,
    repeat_until_timeout, check_text,
)


def authorize_user(page, user: str, password: str):
    """Log in as a specific user. Logs out first if already logged in."""
    page.goto(APP_HOST, wait_until="domcontentloaded")
    logout = page.locator('a[href="/rhn/Logout.do"]')
    try:
        if logout.is_visible(timeout=2000):
            logout.click()
            page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass
    page.locator("#username-field").fill(user)
    page.locator("#password-field").fill(password)
    page.get_by_role("button", name="Sign In").click()
    page.locator('a[href="/rhn/Logout.do"]').wait_for(
        state="visible", timeout=30000)


def follow_link_in_content_area(page, text: str):
    """Click a link within the main content section."""
    page.locator("section").get_by_role("link", name=text).click()
    wait_for_ajax(page)


def follow_left_menu(page, menu_path: str):
    """Navigate the left sidebar. menu_path is 'Top > Sub > Item' or just 'Item'."""
    if page.url == "about:blank":
        page.goto(APP_HOST, wait_until="domcontentloaded")
    parts = [p.strip() for p in menu_path.split(">")]
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        if not is_last:
            # Intermediate section: only expand if next item is not already visible.
            # If already expanded, clicking again would collapse it.
            next_link = page.get_by_role("link", name=parts[i + 1]).first
            try:
                if next_link.is_visible(timeout=500):
                    continue
            except Exception:
                pass
        page.get_by_role("link", name=part).first.click()
    wait_for_ajax(page)


def select_option_from_field(page, option: str, field: str):
    """Select an option from a dropdown/select field by field name or label."""
    for locator_fn in [
        lambda: page.locator(
            f':is(select)[id="{field}"], select[name="{field}"]'
        ).first,
        lambda: page.get_by_role("combobox", name=field).first,
        lambda: page.get_by_label(field).first,
    ]:
        try:
            loc = locator_fn()
            if loc.count() > 0:
                loc.select_option(option)
                return
        except Exception:
            continue
    raise AssertionError(f"Could not find select field '{field}'")


def wait_for_text(page, text: str, *, timeout: int = None):
    """Wait for text to appear on the page."""
    from support.env import DEFAULT_TIMEOUT
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    page.get_by_text(text).first.wait_for(
        state="visible", timeout=timeout * 1000)


def wait_for_text_or(page, text1: str, text2: str):
    """Wait until either of two texts is visible."""
    loc1 = page.get_by_text(text1).first
    loc2 = page.get_by_text(text2).first
    loc1.or_(loc2).wait_for(state="visible")


def wait_for_text_refreshing(page, text: str):
    """Wait for text to appear, refreshing the page on each attempt."""
    def attempt():
        try:
            if page.get_by_text(text).first.is_visible(timeout=3000):
                return True
        except Exception:
            pass
        page.reload()
        return None
    repeat_until_timeout(attempt, message=f"Couldn't find text '{text}'")


def fill_field(page, field: str, value: str):
    """Fill a form field by label."""
    page.get_by_label(field).first.fill(value)


def enter_text_in_field(page, text: str, field: str):
    """Fill a named input field (by name or id attribute)."""
    loc = page.locator(f'input[id="{field}"], input[name="{field}"], textarea[id="{field}"]').first
    loc.fill(text)


def click_on(page, text: str):
    """Click a button or link by visible text or element ID (mirrors Capybara's click_on)."""
    for locator_fn in [
        lambda: page.get_by_role("button", name=text).first,
        lambda: page.get_by_role("link", name=text).first,
        lambda: page.locator(f"#{text}").first,
    ]:
        try:
            loc = locator_fn()
            loc.click(timeout=2000)
            wait_for_ajax(page)
            return
        except Exception:
            continue
    raise AssertionError(f"Could not find button, link, or element with id '{text}'")


def follow_href(page, href: str):
    """Navigate directly to a URL path."""
    page.goto(href, wait_until="domcontentloaded")
    wait_for_ajax(page)
