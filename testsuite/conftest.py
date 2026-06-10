"""Root conftest.py — browser fixtures, tag skipping, hooks."""

pytest_plugins = [
    "step_definitions.api_common",
    "step_definitions.cobbler_steps",
    "step_definitions.command_steps",
    "step_definitions.common_steps",
    "step_definitions.content_lifecycle_steps",
    "step_definitions.datepicker_steps",
    "step_definitions.docker_steps",
    "step_definitions.file_management_steps",
    "step_definitions.https_connection_steps",
    "step_definitions.lock_packages_on_client",
    "step_definitions.navigation_steps",
    "step_definitions.retail_steps",
    "step_definitions.rke2_steps",
    "step_definitions.salt_steps",
    "step_definitions.security_steps",
    "step_definitions.setup_steps",
    "step_definitions.system_monitoring_steps",
]

import os
import re
import time
import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Run-set ordering: parse run_sets/*.yml to get canonical feature file order
# ---------------------------------------------------------------------------

def _build_feature_order() -> dict:
    """Return {abs_feature_path: global_sort_index} from all run_set YAMLs."""
    run_sets_root = Path(__file__).parent / "run_sets"
    order: dict = {}
    index = 0
    for yml in sorted(run_sets_root.rglob("*.yml")):
        for line in yml.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("- features/"):
                abs_path = str(Path(__file__).parent / line[2:])
                if abs_path not in order:
                    order[abs_path] = index
                    index += 1
    return order


_FEATURE_ORDER: dict | None = None
_RUN_SET_ALLOWED: set | None = None


def _feature_sort_key(item) -> int:
    global _FEATURE_ORDER
    if _FEATURE_ORDER is None:
        _FEATURE_ORDER = _build_feature_order()
    func = getattr(item, "function", None)
    bdd_scenario = getattr(func, "__scenario__", None)
    if bdd_scenario is not None:
        return _FEATURE_ORDER.get(str(bdd_scenario.feature.filename), 999999)
    return 999999

from support.env import (
    APP_HOST, CAPYBARA_TIMEOUT, DEBUG_MODE, DEFAULT_TIMEOUT,
    SCREENSHOT_DIR, CODE_COVERAGE_MODE, QUALITY_INTELLIGENCE_MODE,
    IS_CLOUD_PROVIDER, IS_GH_VALIDATION, IS_CONTAINERIZED_SERVER,
    IS_RKE2, USE_SALT_BUNDLE, BETA_ENABLED,
    PXEBOOT_MAC, SLE15SP6_TERMINAL_MAC, PRIVATE_NET, MIRROR,
    SERVER_HTTP_PROXY, CUSTOM_DOWNLOAD_ENDPOINT,
    NO_AUTH_REGISTRY, AUTH_REGISTRY, scc_credentials_valid,
    CHROMIUM_DEV_PORT,
)
from support.constants import ENV_VAR_BY_HOST


# ---------------------------------------------------------------------------
# Browser isolation: ContextManager
# ---------------------------------------------------------------------------

class ContextManager:
    """Manages Playwright browser context with feature-boundary resets and crash recovery."""

    def __init__(self, browser):
        self._browser = browser
        self._context = None

    def get_or_create(self):
        if self._context is None or self._is_crashed():
            self._context = self._new_context()
        return self._context

    def reset(self):
        """Create a fresh context (called at every feature file boundary)."""
        self._safe_close()
        self._context = self._new_context()
        return self._context

    def _new_context(self):
        ctx = self._browser.new_context(
            ignore_https_errors=True,
            base_url=APP_HOST,
            viewport={"width": 2048, "height": 2048},
            accept_downloads=True,
        )
        ctx.set_default_timeout(CAPYBARA_TIMEOUT * 1000)
        return ctx

    def _is_crashed(self):
        try:
            _ = self._context.pages
            return False
        except Exception:
            return True

    def _safe_close(self):
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None


# ---------------------------------------------------------------------------
# Browser fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def playwright_instance():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    args = [
        "--disable-dev-shm-usage",
        "--ignore-certificate-errors",
        "--no-sandbox",
        "--disable-notifications",
        "--window-size=2048,2048",
        "--js-flags=--max-old-space-size=2048",
        "--log-level=3",
    ]
    if not DEBUG_MODE:
        args.append("--headless=new")
    if CHROMIUM_DEV_PORT:
        args.append(f"--remote-debugging-port={CHROMIUM_DEV_PORT}")
    if IS_CLOUD_PROVIDER:
        args.append(f"--user-data-dir=/tmp/chrome_profile_{os.getpid()}")

    executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or None
    b = playwright_instance.chromium.launch(headless=not DEBUG_MODE, args=args,
                                            executable_path=executable_path)
    yield b
    b.close()


@pytest.fixture(scope="session")
def context_manager(browser):
    cm = ContextManager(browser)
    yield cm
    cm._safe_close()


_current_feature = None


def _get_feature_path(request):
    func = getattr(request.node, "function", None)
    scenario = getattr(func, "__scenario__", None)
    if scenario:
        return str(scenario.feature.filename)
    return request.node.nodeid.split("::")[0]


@pytest.fixture(autouse=True)
def feature_boundary(request, context_manager):
    global _current_feature
    feature_path = _get_feature_path(request)
    if feature_path != _current_feature:
        context_manager.reset()
        _current_feature = feature_path
    yield


@pytest.fixture
def page(context_manager, request):
    """One Playwright page per scenario. Closed on teardown regardless of outcome."""
    ctx = context_manager.get_or_create()
    pg = ctx.new_page()
    request.node._playwright_page = pg
    start = time.time()
    yield pg
    duration = time.time() - start
    print(f"Scenario took {duration:.1f}s")
    try:
        pg.close()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def scenario_recovery(request, context_manager):
    """After a failed scenario: clear cookies to prevent state leaking to next scenario."""
    yield
    report = getattr(request.node, "_report", None)
    if report and report.failed:
        try:
            ctx = context_manager.get_or_create()
            ctx.clear_cookies()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Screenshots and server logs on failure
# ---------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item._report = report
    if report.when == "call" and report.failed:
        pg = getattr(item, "_playwright_page", None) or item.funcargs.get("page")
        if pg:
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
            safe_name = re.sub(r"[ ./:]", "_", report.nodeid)[:200]
            path = f"{SCREENSHOT_DIR}/{safe_name}.png"
            try:
                pg.screenshot(path=path)
                print(f"Screenshot saved: {path}")
                try:
                    import base64
                    from pytest_html import extras
                    if not hasattr(report, "extras"):
                        report.extras = []
                    with open(path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    report.extras.append(extras.image(encoded, mime_type="image/png"))
                except Exception:
                    pass
            except Exception as e:
                print(f"Screenshot failed: {e}")
        _print_server_logs()


def _print_server_logs():
    try:
        from support.remote_nodes_env import get_target
        server = get_target("server")
        for log_path in [
            "/var/log/rhn/rhn_web_ui.log",
            "/var/log/rhn/rhn_web_api.log",
        ]:
            cmd = (
                f"tail -n20 {log_path} | "
                f"awk -v limit=\"$(date --date='5 minutes ago' '+%Y-%m-%d %H:%M:%S')\" "
                f"'substr($0, 1, 19) > limit'"
            )
            out, _code = server.run(cmd, timeout=10, check_errors=False)
            print(f"=> {log_path}\n{out}")
    except Exception as e:
        print(f"Could not fetch server logs: {e}")


# ---------------------------------------------------------------------------
# Tag system — session cache for SSH-dependent conditions
# ---------------------------------------------------------------------------

_session_cache: dict = {}


def _init_session_cache():
    """Evaluate SSH-dependent tag conditions once at session start. Fails gracefully."""
    try:
        from support.commonlib import product as _product
        _session_cache["product"] = _product()
    except Exception:
        _session_cache["product"] = ""
    try:
        from support.commonlib import product_version_full
        _session_cache["product_version"] = product_version_full() or ""
    except Exception:
        _session_cache["product_version"] = ""
    try:
        from support.remote_nodes_env import get_target
        server = get_target("server")
        _out, code = server.run(
            'grep \'"scc_access_logging": true\' /etc/salt/grains',
            check_errors=False)
        _session_cache["scc_access_logging"] = (code == 0)
    except Exception:
        _session_cache["scc_access_logging"] = False
    try:
        from support.commonlib import transactional_system
        _session_cache["is_transactional_server"] = transactional_system(
            "server", runs_in_container=False)
    except Exception:
        _session_cache["is_transactional_server"] = False


# Host presence tags: every key in ENV_VAR_BY_HOST except 'localhost'
_HOST_TAG_MAP = {host: host for host in ENV_VAR_BY_HOST if host != "localhost"}

# Boolean condition tags: tag name -> callable returning True=run, False=skip
_BOOL_TAG_MAP = {
    "skip":                          lambda: False,
    "skip_known_issue":              lambda: False,
    "susemanager":                   lambda: _session_cache.get("product") == "SUSE Manager",
    "uyuni":                         lambda: _session_cache.get("product") == "Uyuni",
    "head":                          lambda: _session_cache.get("product_version") == "head",
    "skip_if_cloud":                 lambda: not IS_CLOUD_PROVIDER,
    "cloud":                         lambda: IS_CLOUD_PROVIDER,
    "skip_if_github_validation":     lambda: not IS_GH_VALIDATION,
    "skip_if_containerized_server":  lambda: not IS_CONTAINERIZED_SERVER,
    "containerized_server":          lambda: IS_CONTAINERIZED_SERVER,
    "rke2":                          lambda: IS_RKE2,
    "skip_if_transactional_server":  lambda: not _session_cache.get("is_transactional_server", False),
    "transactional_server":          lambda: _session_cache.get("is_transactional_server", False),
    "salt_bundle":                   lambda: USE_SALT_BUNDLE,
    "skip_if_salt_bundle":           lambda: not USE_SALT_BUNDLE,
    "scc_credentials":               lambda: scc_credentials_valid,
    "private_net":                   lambda: bool(PRIVATE_NET),
    "no_mirror":                     lambda: not bool(MIRROR),
    "server_http_proxy":             lambda: bool(SERVER_HTTP_PROXY),
    "custom_download_endpoint":      lambda: bool(CUSTOM_DOWNLOAD_ENDPOINT),
    "no_auth_registry":              lambda: bool(NO_AUTH_REGISTRY),
    "auth_registry":                 lambda: bool(AUTH_REGISTRY),
    "beta":                          lambda: BETA_ENABLED,
    "pxeboot_minion":                lambda: bool(PXEBOOT_MAC),
    "sle15sp6_terminal":             lambda: bool(SLE15SP6_TERMINAL_MAC),
    "sle15sp7_terminal":             lambda: bool(SLE15SP6_TERMINAL_MAC),  # same var, intentional
    "srv_scc_access_logging":        lambda: _session_cache.get("scc_access_logging", False),
}

# Context tags: tag name -> callable(item) returning True=skip
_CONTEXT_TAG_MAP = {
    "slemicro":                    lambda item: "slemicro" not in str(item.fspath),
    "suse_minion":                 lambda item: not (
        "minion" in str(item.fspath)
        and ("sle" in str(item.fspath) or "suse" in str(item.fspath))
    ),
    "transactional_minion":        lambda item: not (
        "slemicro" in str(item.fspath) or "slmicro" in str(item.fspath)
    ),
    "skip_for_debian":             lambda item: "debian" in str(item.fspath),
    "skip_for_ubuntu":             lambda item: "ubuntu" in str(item.fspath),
    "skip_for_amazon2023":         lambda item: "amazon2023" in str(item.fspath),
    "skip_for_minion":             lambda item: "minion" in str(item.fspath),
    "skip_for_transactional_minion": lambda item: (
        "slemicro" in str(item.fspath) or "slmicro" in str(item.fspath)
    ),
}

_RHEL10_TAGS = {
    "alma10_minion", "alma10_ssh_minion",
    "oracle10_minion", "oracle10_ssh_minion",
    "rocky10_minion", "rocky10_ssh_minion",
}


def pytest_addoption(parser):
    parser.addoption(
        "--run-set",
        action="store",
        default=None,
        metavar="NAME",
        help=(
            "Run only the features listed in run_sets/<NAME>.yml, in order. "
            "Equivalent to 'rake cucumber:<NAME>'. "
            "Example: --run-set=core, --run-set=sanity_check"
        ),
    )


def _load_run_set(name: str) -> list[str]:
    """Return ordered list of absolute feature file paths for a run_set name."""
    run_sets_root = Path(__file__).parent / "run_sets"
    matches = list(run_sets_root.rglob(f"{name}.yml"))
    if not matches:
        raise ValueError(f"Run set '{name}' not found under {run_sets_root}")
    yml = matches[0]
    paths = []
    for line in yml.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("- features/"):
            paths.append(str(Path(__file__).parent / line[2:]))
    return paths


def pytest_ignore_collect(collection_path, config):
    """Skip directories that contain no feature files from the active run-set."""
    global _RUN_SET_ALLOWED
    run_set_name = config.getoption("--run-set", default=None)
    if not run_set_name or not collection_path.is_dir():
        return None
    if _RUN_SET_ALLOWED is None:
        try:
            _RUN_SET_ALLOWED = set(_load_run_set(run_set_name))
        except ValueError:
            _RUN_SET_ALLOWED = set()
    if not _RUN_SET_ALLOWED:
        return None
    path_prefix = str(collection_path) + "/"
    if any(p.startswith(path_prefix) for p in _RUN_SET_ALLOWED):
        return None
    return True


def pytest_configure(config):
    """Register all tag markers and populate session cache."""
    for tag in _HOST_TAG_MAP:
        config.addinivalue_line("markers", f"{tag}: requires {tag} host")
    for tag in _BOOL_TAG_MAP:
        config.addinivalue_line("markers", f"{tag}: condition-based skip")
    for tag in _CONTEXT_TAG_MAP:
        config.addinivalue_line("markers", f"{tag}: file-path-based skip")
    config.addinivalue_line("markers", "scope_cobbler: attach cobbler log on failure")
    config.addinivalue_line("markers", "skip_for_rhel10plus: skip on rhel10+ targets")
    config.addinivalue_line(
        "markers",
        "run_if_proxy_transactional_or_slmicro62_minion: compound condition")
    config.addinivalue_line(
        "markers",
        "run_if_proxy_not_transactional_or_sles15sp7_minion: compound condition")
    config.addinivalue_line(
        "markers",
        "flaky: marks scenarios known to be occasionally flaky (informational only, no skip)")
    _init_session_cache()


def pytest_collection_modifyitems(config, items):
    run_set_name = config.getoption("--run-set", default=None)
    if run_set_name:
        allowed = set(_load_run_set(run_set_name))
        selected, deselected = [], []
        for item in items:
            func = getattr(item, "function", None)
            bdd_scenario = getattr(func, "__scenario__", None)
            if bdd_scenario is not None and str(bdd_scenario.feature.filename) in allowed:
                selected.append(item)
            else:
                deselected.append(item)
        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

    for item in items:
        func = getattr(item, "function", None)
        bdd_scenario = getattr(func, "__scenario__", None)
        if bdd_scenario is not None:
            item.extra_keyword_matches.add(Path(bdd_scenario.feature.filename).stem)

        markers = {m.name for m in item.iter_markers()}

        # Host presence tags
        for tag in markers & set(_HOST_TAG_MAP):
            env_var = ENV_VAR_BY_HOST.get(_HOST_TAG_MAP[tag])
            if not env_var or env_var not in os.environ:
                item.add_marker(pytest.mark.skip(
                    reason=f"Host '{tag}' not present (env var {env_var} not set)"))
                break

        # Boolean condition tags
        for tag in markers & set(_BOOL_TAG_MAP):
            if not _BOOL_TAG_MAP[tag]():
                item.add_marker(pytest.mark.skip(
                    reason=f"Condition @{tag} not met"))
                break

        # Context/file-path tags
        for tag in markers & set(_CONTEXT_TAG_MAP):
            if _CONTEXT_TAG_MAP[tag](item):
                item.add_marker(pytest.mark.skip(
                    reason=f"@{tag} excluded for this feature path"))
                break

        # skip_for_rhel10plus
        if "skip_for_rhel10plus" in markers and markers & _RHEL10_TAGS:
            item.add_marker(pytest.mark.skip(reason="@skip_for_rhel10plus"))

        # Compound: run_if_proxy_transactional_or_slmicro62_minion
        if "run_if_proxy_transactional_or_slmicro62_minion" in markers:
            proxy_transactional = _session_cache.get("is_transactional_server", False)
            slmicro62_env = ENV_VAR_BY_HOST.get("slmicro62_minion", "")
            slmicro62_present = bool(os.environ.get(slmicro62_env))
            if not proxy_transactional and not slmicro62_present:
                item.add_marker(pytest.mark.skip(
                    reason="@run_if_proxy_transactional_or_slmicro62_minion not met"))

        # Compound: run_if_proxy_not_transactional_or_sles15sp7_minion
        if "run_if_proxy_not_transactional_or_sles15sp7_minion" in markers:
            proxy_not_transactional = not _session_cache.get("is_transactional_server", False)
            sp7_env = ENV_VAR_BY_HOST.get("sle15sp7_minion", "")
            sp7_present = bool(os.environ.get(sp7_env))
            if not proxy_not_transactional and not sp7_present:
                item.add_marker(pytest.mark.skip(
                    reason="@run_if_proxy_not_transactional_or_sles15sp7_minion not met"))

    # Sort by run_set order (stable: scenarios within a feature keep their relative order)
    items.sort(key=_feature_sort_key)


# ---------------------------------------------------------------------------
# Hooks: cobbler log, feature user creation, AJAX wait
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def cobbler_log_on_failure(request):
    yield
    marker = request.node.get_closest_marker("scope_cobbler")
    report = getattr(request.node, "_report", None)
    if marker and report and report.failed:
        try:
            from support.remote_nodes_env import get_target
            server = get_target("server")
            out, _code = server.run(
                "tail -n20 /var/log/cobbler/cobbler.log", check_errors=False)
            print(f"=> /var/log/cobbler/cobbler.log\n{out}")
        except Exception as e:
            print(f"Could not fetch cobbler log: {e}")


_context_store: dict = {}


@pytest.fixture
def feature_context():
    """Global key-value store shared across all steps (replaces Ruby's $context)."""
    return _context_store


@pytest.fixture(autouse=True)
def create_feature_user(request):
    """Create a per-feature user via API (mirrors Ruby's Before hook)."""
    feature_path = _get_feature_path(request)
    if re.search(r"core|reposync|finishing|build_validation", feature_path):
        yield
        return
    feature_name = Path(feature_path).stem
    context_key = f"user_created_{feature_name}"
    if not _context_store.get(context_key):
        try:
            from support.api_test import new_api_client
            api = new_api_client()
            api.call("user.create", feature_name, "linux",
                     feature_name, f"{feature_name}@test.local", 0)
        except Exception:
            pass  # user may already exist
        _context_store[context_key] = True
    yield


@pytest.fixture(scope="session")
def api_test():
    """Session-scoped API client."""
    from support.api_test import new_api_client
    return new_api_client()


@pytest.fixture
def scenario_state():
    """Per-scenario mutable dict replacing Ruby's @instance_vars pattern."""
    return {}


# ---------------------------------------------------------------------------
# Reporting: code coverage and quality intelligence
# ---------------------------------------------------------------------------

_code_coverage = None
_quality_intelligence = None

if CODE_COVERAGE_MODE:
    try:
        from support.code_coverage import CodeCoverage
        _code_coverage = CodeCoverage()
    except Exception as e:
        print(f"Warning: Could not initialize code coverage: {e}")

if QUALITY_INTELLIGENCE_MODE:
    try:
        from support.quality_intelligence import QualityIntelligence
        _quality_intelligence = QualityIntelligence()
    except Exception as e:
        print(f"Warning: Could not initialize quality intelligence: {e}")


@pytest.fixture(scope="session")
def quality_intelligence():
    return _quality_intelligence


_coverage_feature_path = None


if CODE_COVERAGE_MODE:
    @pytest.hookimpl(tryfirst=True)
    def pytest_bdd_before_scenario(request, feature, scenario):
        global _coverage_feature_path
        if not _code_coverage:
            return
        feature_path = str(feature.filename)
        if _coverage_feature_path and _coverage_feature_path != feature_path:
            _process_coverage(_coverage_feature_path)
        _coverage_feature_path = feature_path


def pytest_sessionfinish(session, exitstatus):
    if _code_coverage and _coverage_feature_path:
        _process_coverage(_coverage_feature_path)


def _process_coverage(feature_path: str):
    feature_name = Path(feature_path).stem
    try:
        _code_coverage.jacoco_dump(feature_name)
        _code_coverage.push_feature_coverage(feature_name)
    except Exception as e:
        print(f"Warning: Code coverage processing failed: {e}")
