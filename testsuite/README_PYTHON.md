# Uyuni Testsuite — Python/Playwright Runner

This document covers the Python/Playwright/pytest-bdd implementation of the Uyuni testsuite.
The original Ruby/Capybara implementation is documented in [README.md](README.md).

The Gherkin `.feature` files are shared between both runners and are not modified.

---

## Requirements

### Python

Python 3.11 or later.

### System dependencies

Chromium and its system libraries are required for Playwright's browser automation:

```bash
# openSUSE / SLES
zypper install chromium

# Or let Playwright install a managed browser (see Installation below)
```

### Python dependencies

All dependencies are declared in `pyproject.toml`:

| Package | Version | Purpose |
|---|---|---|
| `pytest` | ≥7.4 | Test runner |
| `pytest-bdd` | ≥7.0 | BDD step wiring to `.feature` files |
| `playwright` | ≥1.40 | Browser automation (replaces Capybara + Selenium) |
| `paramiko` | ≥3.4 | SSH connections to test nodes |
| `httpx` | ≥0.27 | HTTP API client |
| `prometheus-client` | ≥0.20 | Quality Intelligence metrics push |
| `redis` | ≥5.0 | Code coverage tracking (optional) |
| `pytest-html` | ≥4.0 | HTML test report |

---

## Installation

```bash
cd /path/to/testsuite

# Install Python dependencies
pip install -e .

# Install Playwright's managed Chromium browser
playwright install chromium
playwright install-deps chromium   # installs system libs on Linux
```

On CI workers, add these steps to the Dockerfile or worker provisioning script instead of running them manually.

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

The full list of host variables is in `support/constants.py` (`ENV_VAR_BY_HOST`). Scenarios tagged with a host that has no env var set are automatically skipped — you do not need to set variables for hosts that are absent.

### Authentication

| Variable | Default | Description |
|---|---|---|
| `MANAGER_USER` | `admin` | SUMA/Uyuni web UI username |
| `MANAGER_PASSWORD` | `admin` | SUMA/Uyuni web UI password |

### Optional feature flags

| Variable | Values | Description |
|---|---|---|
| `DEBUG` | `true` | Run browser in headed (visible) mode |
| `REMOTE_DEBUG` | `true` | Enable Chromium remote DevTools on port 9222 |
| `CAPYBARA_TIMEOUT` | integer (seconds) | Browser wait timeout (default: 10) |
| `DEFAULT_TIMEOUT` | integer (seconds) | SSH/polling timeout (default: 250) |
| `SCREENSHOT_DIR` | path | Directory for failure screenshots (default: `screenshots/`) |
| `PROVIDER` | `aws`, `podman`, … | Cloud/container provider — controls `@cloud`, `@skip_if_cloud` tags |
| `CONTAINER_RUNTIME` | `k3s`, `podman`, `rke2` | Controls `@containerized_server`, `@rke2` tags |
| `USE_SALT_BUNDLE` | `true`/`false` | Controls `@salt_bundle`/`@skip_if_salt_bundle` tags (default: true) |
| `PRIVATENET` | network prefix | Enables private network address resolution |
| `MIRROR` | hostname | Mirror server — controls `@no_mirror` tag |
| `SCC_CREDENTIALS` | `user\|password` | SCC credentials — controls `@scc_credentials` tag |
| `BETA_ENABLED` | `True`/`False` | Enable beta channel scenarios |
| `API_PROTOCOL` | `http` or unset | Force HTTP for API calls (default: XMLRPC over HTTPS) |

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

### A feature group

```bash
pytest features/core/ -v
pytest features/secondary/ -v
pytest features/init_clients/ -v
```

### Single feature file

```bash
pytest features/core/srv_disable_local_repos_off.feature -v
```

### Multiple specific features

```bash
pytest \
  features/core/srv_disable_local_repos_off.feature \
  features/secondary/allcli_action_chain.feature \
  -v
```

### Validation slices (recommended first run)

These four features cover SSH, browser, API, and tag-skipping — run them first to confirm infrastructure is working before running the full suite:

```bash
pytest \
  features/core/srv_disable_local_repos_off.feature \
  features/secondary/allcli_action_chain.feature \
  features/secondary/min_config_state_channel_api.feature \
  features/init_clients/sle_minion.feature \
  -v
```

### Dry run (collect without executing)

```bash
pytest features/ --collect-only -q
```

This resolves all step definitions without connecting to any server. Use it to catch undefined steps.

### Debug mode (headed browser)

```bash
DEBUG=true pytest features/secondary/allcli_action_chain.feature -v
```

---

## Test output

| Path | Format | Description |
|---|---|---|
| `results/output.json` | Cucumber JSON | Consumed by RRTG for CI triage |
| `results_junit/output.xml` | JUnit XML | Jenkins test result integration |
| `results/output.html` | HTML | Human-readable report |
| `screenshots/` | PNG | Captured automatically on scenario failure |
| `api.log` | Text | All XML-RPC/HTTP API calls with timestamps |

---

## Tag system

Scenarios are skipped automatically based on deployment state. No manual `--tags` filtering is needed — just set (or omit) the host env vars and the relevant flags.

| Tag category | How it works |
|---|---|
| Host presence (`@sle_minion`, `@proxy`, …) | Skipped if the corresponding env var is not set |
| Boolean conditions (`@susemanager`, `@cloud`, `@salt_bundle`, …) | Skipped based on env vars or SSH-detected product info |
| File-path conditions (`@skip_for_debian`, `@slemicro`, …) | Skipped based on the feature file's path |
| Informational (`@flaky`, `@scope_*`) | No skip behavior — metadata only |

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

Unlike the Ruby/Selenium runner (which shared one browser session across the entire run), the Python runner uses **feature-scoped browser contexts**:

- A single Chromium process runs for the whole session.
- A fresh browser context (cookies, storage, cache) is created at the start of each feature file.
- Each scenario gets its own tab (`page` fixture), closed after the scenario regardless of outcome.
- On scenario failure: cookies are cleared before the next scenario.
- On browser crash: the context is automatically replaced.

This eliminates the chain-failure problem where one failing WebUI test corrupted the session for subsequent scenarios.

### Project layout

```
testsuite/
├── conftest.py              # Browser fixtures, tag system, all hooks
├── pytest.ini               # pytest configuration
├── pyproject.toml           # Dependencies
├── features/                # Gherkin .feature files (unchanged, shared with Ruby runner)
├── step_definitions/        # Python step implementations
│   ├── command_steps.py     # SSH/command steps (no browser)
│   ├── navigation_steps.py  # Browser UI steps
│   ├── api_common.py        # XML-RPC API steps
│   ├── salt_steps.py        # Salt-specific steps
│   └── ...                  # 17 files total
└── support/                 # Infrastructure
    ├── env.py               # Environment variable config
    ├── constants.py         # All data maps (hosts, channels, packages)
    ├── commonlib.py         # repeat_until_timeout, check_text, helpers
    ├── remote_node.py       # SSH node abstraction (paramiko)
    ├── remote_nodes_env.py  # get_target() factory
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

**`ModuleNotFoundError: No module named 'pytest_bdd'`**
Run `pip install -e .` from the `testsuite/` directory.

**`Error: Executable doesn't exist at ...chromium...`**
Run `playwright install chromium`.

**Scenario fails immediately with SSH error**
Check that `SERVER` env var is set and the server is reachable: `ssh root@$SERVER hostname`

**All scenarios in a feature are skipped**
The feature requires a host that is not in your environment. Check which `@tag` the feature uses and whether the corresponding env var is set.

**Screenshots are blank or show a login page**
The browser context was not logged in. Check that `MANAGER_USER`/`MANAGER_PASSWORD` are correct and that the `authorize_user()` embedded step is being called at the start of the feature.

**`TimeoutError` in `repeat_until_timeout`**
Increase `DEFAULT_TIMEOUT` or `CAPYBARA_TIMEOUT` env vars. The defaults (250s and 10s) match the Ruby suite.
