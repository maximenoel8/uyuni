# Uyuni Testsuite — Python/Playwright Runner

This document covers the Python/Playwright/pytest-bdd implementation of the Uyuni testsuite.
The original Ruby/Capybara implementation is documented in [README.md](README.md).

The Gherkin `.feature` files are shared between both runners and are not modified.

---

## Requirements

### Python

Python 3.11 or later.

### System dependencies

A Chromium browser is required for Playwright's browser automation.

**openSUSE / SLES (recommended — use system Chromium):**
```bash
zypper install chromium
```
Then set the env var so Playwright uses the system browser instead of downloading its own:
```bash
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
```

**Ubuntu / Debian (official Playwright support):**
```bash
playwright install chromium
playwright install-deps chromium
```

> **Note:** `playwright install-deps` uses `apt-get` and will fail on openSUSE/SLES.
> Use the system Chromium approach above on those distributions.

---

## Installation

```bash
cd /path/to/testsuite

# Install Python dependencies
pip install -e .

# openSUSE/SLES — use system Chromium, skip Playwright browser download
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# Ubuntu/Debian only — download Playwright's managed Chromium
# playwright install chromium
# playwright install-deps chromium
```

On CI workers, set `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` and install Chromium via the
distribution package manager instead of running `playwright install-deps`.

---

## Environment variables

### Required

| Variable | Description |
|---|---|
| `SERVER` | Hostname or IP of the SUMA/Uyuni server |

### Test node hosts (set the ones present in your environment)

| Variable | Host role |
|---|---|
| `PROXY` | Proxy node |
| `MINION` | SLE minion |
| `SSH_MINION` | SSH-managed minion |
| `RHLIKE_MINION` | Red Hat-like minion |
| `DEBLIKE_MINION` | Debian-like minion |
| `BUILD_HOST` | Container build host |
| `SLE15SP7_MINION` | SLE 15 SP7 minion |
| `SLE15SP7_SSHMINION` | SLE 15 SP7 SSH minion |
| `MONITORING_SERVER` | Monitoring node |

The full list of host variables is in `support/constants.py` (`ENV_VAR_BY_HOST`).
Scenarios tagged with a host that has no env var set are automatically skipped.

### Authentication

| Variable | Default | Description |
|---|---|---|
| `MANAGER_USER` | `admin` | SUMA/Uyuni web UI username |
| `MANAGER_PASSWORD` | `admin` | SUMA/Uyuni web UI password |

### Browser

| Variable | Default | Description |
|---|---|---|
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | _(unset)_ | Path to system Chromium binary — use on openSUSE/SLES |
| `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` | _(unset)_ | Set to `1` to skip Playwright's browser download |
| `DEBUG` | _(unset)_ | Set to `true` to run browser in headed (visible) mode |
| `REMOTE_DEBUG` | _(unset)_ | Set to `true` to enable Chromium remote DevTools on port 9222 |
| `CAPYBARA_TIMEOUT` | `10` | Browser wait timeout in seconds |

### Infrastructure

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_TIMEOUT` | `250` | SSH/polling timeout in seconds |
| `SCREENSHOT_DIR` | `screenshots/` | Directory for failure screenshots |
| `PROVIDER` | _(unset)_ | Cloud/container provider (`aws`, `podman`, …) — controls `@cloud`, `@skip_if_cloud` tags |
| `CONTAINER_RUNTIME` | _(unset)_ | `k3s`, `podman`, or `rke2` — controls `@containerized_server`, `@rke2` tags |
| `USE_SALT_BUNDLE` | `true` | Controls `@salt_bundle`/`@skip_if_salt_bundle` tags |
| `PRIVATENET` | _(unset)_ | Network prefix — enables private network address resolution |
| `MIRROR` | _(unset)_ | Mirror server hostname — controls `@no_mirror` tag |
| `SCC_CREDENTIALS` | _(unset)_ | `user\|password` — controls `@scc_credentials` tag |
| `BETA_ENABLED` | _(unset)_ | Set to `True` to enable beta channel scenarios |
| `API_PROTOCOL` | _(unset)_ | Set to `http` to force HTTP for API calls |

### Reporting (optional)

| Variable | Description |
|---|---|
| `QUALITY_INTELLIGENCE` | `true` — push timing metrics to Prometheus |
| `PROMETHEUS_PUSH_GATEWAY_URL` | Prometheus push gateway URL (default: `http://nsa.mgr.suse.de:9091`) |
| `CODE_COVERAGE` | `true` — extract JaCoCo code coverage after each feature |
| `REDIS_HOST` | Redis host for code coverage storage |
| `REDIS_PORT` | Redis port |
| `REDIS_USERNAME` | Redis username |
| `REDIS_PASSWORD` | Redis password |

---

## Running the tests

All commands must be run from the `testsuite/` directory.

### Full suite

```bash
pytest features/ -v
```

### A feature directory

```bash
pytest features/core/ -v
pytest features/secondary/ -v
pytest features/init_clients/ -v
```

### Single feature file

Each feature directory has its own `test_features.py`. Filter by the feature file's stem
(filename without `.feature`) using `-k`:

```bash
pytest features/core/test_features.py -k "srv_first_settings" -v
pytest features/secondary/test_features.py -k "allcli_action_chain" -v
```

The `-k` filter matches the feature file stem because `conftest.py` adds it to each
test item's keyword set at collection time. All scenarios from that feature file are
selected; scenarios from other files in the same directory are deselected.

> **Note:** Passing a `.feature` path directly to pytest does not work — pytest cannot
> collect test items from Gherkin files. Always target the `test_features.py` in the
> same directory and filter with `-k "feature_stem"`.

### HTML report with embedded screenshots

Generate a self-contained HTML report (similar to Cucumber's HTML report). On failure,
the screenshot taken at the moment of the error is embedded directly in the report:

```bash
pytest features/core/test_features.py -k "srv_first_settings" -v \
    --html=report.html --self-contained-html
```

Open `report.html` in a browser. Each failed scenario shows:
- The full Python traceback
- The Playwright step that timed out
- An embedded screenshot of the browser at the moment of failure

The `--self-contained-html` flag bundles all assets (including screenshots as base64) into
a single file you can copy off the controller without needing the `screenshots/` directory.

### Dry run (collect without executing)

```bash
pytest features/ --collect-only -q
```

This resolves all step definitions without connecting to any server. Use it to catch
undefined or ambiguous steps.

### Debug mode (headed browser)

```bash
DEBUG=true pytest features/secondary/ -k "allcli_action_chain" -v
```

---

## Test output

| Path | Format | Description |
|---|---|---|
| `screenshots/` | PNG | Captured automatically on scenario failure |
| `report.html` | HTML | Self-contained report with embedded screenshots (pass `--html=report.html --self-contained-html`) |
| `api.log` | Text | All XML-RPC/HTTP API calls with timestamps |

---

## Tag system

Scenarios are skipped automatically based on deployment state. No manual `--tags`
filtering is needed — set (or omit) host env vars and the runner skips the rest.

| Tag category | How it works |
|---|---|
| Host presence (`@sle_minion`, `@proxy`, …) | Skipped if the corresponding env var is not set |
| Boolean conditions (`@susemanager`, `@cloud`, `@salt_bundle`, …) | Skipped based on env vars or SSH-detected product info |
| File-path conditions (`@skip_for_debian`, `@slemicro`, …) | Skipped based on the feature file's path |
| Informational (`@flaky`, `@scope_*`) | No skip behaviour — metadata only |

To verify that all tags in the feature files have handlers:

```bash
python -c "
import sys, re, pathlib
sys.path.insert(0, '.')
from conftest import _HOST_TAG_MAP, _BOOL_TAG_MAP, _CONTEXT_TAG_MAP
handled = set(_HOST_TAG_MAP) | set(_BOOL_TAG_MAP) | set(_CONTEXT_TAG_MAP)
handled.update(['scope_cobbler', 'skip_for_rhel10plus', 'flaky',
    'run_if_proxy_transactional_or_slmicro62_minion',
    'run_if_proxy_not_transactional_or_sles15sp7_minion'])
tags = set()
for f in pathlib.Path('features').rglob('*.feature'):
    for line in f.read_text(errors='replace').splitlines():
        s = line.strip()
        if s.startswith('@'):
            for t in re.findall(r'@([a-z_0-9]+)', s):
                tags.add(t)
handled.update(t for t in tags if t.startswith('scope_'))
unhandled = sorted(tags - handled)
print('Unhandled tags:', unhandled or 'none')
"
```

---

## Architecture

### Browser isolation

Unlike the Ruby/Selenium runner (which shared one browser session across the entire run),
the Python runner uses **feature-scoped browser contexts**:

- A single Chromium process runs for the whole session.
- A fresh browser context (cookies, storage, cache) is created at the start of each feature file.
- Each scenario gets its own tab (`page` fixture), closed after the scenario regardless of outcome.
- On scenario failure: cookies are cleared before the next scenario.
- On browser crash: the context is automatically replaced.

This eliminates the chain-failure problem where one failing WebUI test corrupted the
session for subsequent scenarios.

### Step definition discovery

pytest-bdd does not auto-discover `.feature` files. The entry point is `test_features.py`
at the testsuite root, which calls `scenarios()` for every feature directory. Step
definitions are loaded via the `pytest_plugins` list in `conftest.py`.

### Project layout

```
testsuite/
├── conftest.py              # Browser fixtures, tag system, all hooks
├── test_features.py         # Entry point — wires all .feature files to pytest-bdd
├── pytest.ini               # pytest configuration
├── pyproject.toml           # Dependencies (packages: support/, step_definitions/ only)
├── features/                # Gherkin .feature files (unchanged, shared with Ruby runner)
│   ├── core/
│   ├── init_clients/
│   ├── secondary/
│   ├── build_validation/
│   └── ...
├── step_definitions/        # Python step implementations (17 files)
│   ├── command_steps.py     # SSH commands, package ops, repo ops
│   ├── navigation_steps.py  # Browser UI — links, forms, text assertions
│   ├── api_common.py        # XML-RPC API steps
│   ├── salt_steps.py        # Salt key management, minion control
│   ├── setup_steps.py       # Bootstrap, channel setup, onboarding
│   ├── cobbler_steps.py     # PXE/Cobbler provisioning
│   ├── security_steps.py    # OpenSCAP, CVE, audit steps
│   ├── content_lifecycle_steps.py
│   ├── docker_steps.py
│   ├── file_management_steps.py
│   ├── https_connection_steps.py
│   ├── lock_packages_on_client.py
│   ├── retail_steps.py
│   ├── rke2_steps.py
│   ├── datepicker_steps.py
│   ├── system_monitoring_steps.py
│   └── __init__.py
└── support/                 # Infrastructure
    ├── env.py               # All environment variable config
    ├── constants.py         # Data maps: hosts, channels, packages, base channels
    ├── commonlib.py         # repeat_until_timeout, check_text, helpers
    ├── remote_node.py       # SSH node abstraction (paramiko)
    ├── remote_nodes_env.py  # get_target() / get_system_name() factory
    ├── network_utils.py     # Low-level SSH/SCP
    ├── xmlrpc_client.py     # XML-RPC client
    ├── http_client.py       # HTTP API client
    ├── api_test.py          # Unified API client + session management
    ├── namespaces/          # One file per XML-RPC namespace (11 files)
    ├── embedded_steps/      # Shared step logic (replaces Ruby step() calls)
    ├── navigation_helper.py # Checkbox, filter, scoped locator helpers
    ├── file_management.py   # Remote file operations
    ├── code_coverage.py     # JaCoCo + Redis integration
    ├── quality_intelligence.py # Prometheus metrics
    └── custom_formatter.py  # Feature-name-prefixed console output
```

### Capybara → Playwright equivalents

| Capybara (Ruby) | Playwright Python |
|---|---|
| `visit(url)` | `page.goto(url)` |
| `find('#id')` | `page.locator('#id')` |
| `find(..., match: :first)` | `page.locator(...).first` |
| `click_button(text)` | `page.get_by_role("button", name=text).click()` |
| `click_link(text)` | `page.get_by_role("link", name=text).click()` |
| `fill_in(field, with: val)` | `page.get_by_label(field).fill(val)` |
| `has_content?(text)` | `page.get_by_text(text).first.is_visible()` |
| `within('#sel') { ... }` | `scope = page.locator('#sel'); scope.locator(...)` |
| `step %(I am authorized as "x")` | `authorize_user(page, x, password)` |

---

## Troubleshooting

**`error: Multiple top-level packages discovered in a flat-layout`**
This was a setuptools discovery issue. It is fixed in `pyproject.toml` via:
```toml
[tool.setuptools.packages.find]
include = ["support*", "step_definitions*"]
```
Run `pip install -e .` again after pulling the fix.

**`playwright install-deps` fails with `sh: apt-get: command not found`**
`playwright install-deps` only supports Debian/Ubuntu. On openSUSE/SLES, use the system
Chromium instead:
```bash
zypper install chromium
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
```

**`Error: Executable doesn't exist at ...chromium...`**
Either run `playwright install chromium` (Ubuntu/Debian) or set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to the path of your system Chromium binary.

**`ModuleNotFoundError: No module named 'pytest_bdd'`**
Run `pip install -e .` from the `testsuite/` directory.

**`no tests collected`**
pytest-bdd requires `test_features.py` to be present at the testsuite root. It calls
`scenarios()` to bind all `.feature` files. If it is missing, no tests are collected.

**Step shows as undefined in IDE**
The IDE Gherkin plugin only recognises `@given`, `@when`, `@then` — not pytest-bdd's
`@step`. Use stacked decorators instead:
```python
@when(parsers.re(r'my step "(?P<x>[^"]*)"'))
@given(parsers.re(r'my step "(?P<x>[^"]*)"'))
def my_step(x: str): ...
```

**Scenario fails immediately with SSH error**
Check that `SERVER` env var is set and the server is reachable:
```bash
ssh root@$SERVER hostname
```

**All scenarios in a feature are skipped**
The feature requires a host not in your environment. Check which `@tag` the feature uses
and whether the corresponding env var is set. Run `--collect-only -q` to see which
scenarios would be collected.

**Screenshots are blank or show a login page**
The browser context was not logged in. Check that `MANAGER_USER`/`MANAGER_PASSWORD` are
correct and that `authorize_user()` is called at the start of the feature.

**`TimeoutError` in `repeat_until_timeout`**
Increase `DEFAULT_TIMEOUT` or `CAPYBARA_TIMEOUT` env vars. The defaults (250 s and 10 s)
match the Ruby suite timing.
