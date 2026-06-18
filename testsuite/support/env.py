import json
import os
from pathlib import Path

DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "250"))
CAPYBARA_TIMEOUT = int(os.getenv("CAPYBARA_TIMEOUT", "10"))
CODE_COVERAGE_MODE = os.getenv("CODE_COVERAGE", "").lower() == "true"
QUALITY_INTELLIGENCE_MODE = os.getenv("QUALITY_INTELLIGENCE", "").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG", "").lower() == "true"
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")

SERVER = os.getenv("SERVER", "")
APP_HOST = f"https://{SERVER}"

IS_CLOUD_PROVIDER = "aws" in os.getenv("PROVIDER", "")
IS_GH_VALIDATION = "podman" in os.getenv("PROVIDER", "")
IS_CONTAINERIZED_SERVER = os.getenv("CONTAINER_RUNTIME", "") in ("k3s", "podman")
IS_RKE2 = "rke2" in os.getenv("CONTAINER_RUNTIME", "")
IS_USING_BUILD_IMAGE = os.getenv("IS_USING_BUILD_IMAGE", "").lower() == "true"
IS_USING_SCC_REPOSITORIES = os.getenv("IS_USING_SCC_REPOSITORIES", "False").lower() == "true"
BETA_ENABLED = os.getenv("BETA_ENABLED", "False").lower() == "true"
USE_SALT_BUNDLE = os.getenv("USE_SALT_BUNDLE", "true").lower() == "true"
API_PROTOCOL = os.getenv("API_PROTOCOL")

PXEBOOT_MAC = os.getenv("PXEBOOT_MAC")
PXEBOOT_IMAGE = os.getenv("PXEBOOT_IMAGE", "sles15sp3o")
SLE15SP6_TERMINAL_MAC = os.getenv("SLE15SP6_TERMINAL_MAC")
SLE15SP7_TERMINAL_MAC = os.getenv("SLE15SP7_TERMINAL_MAC")
PRIVATE_NET = os.getenv("PRIVATENET")
MIRROR = os.getenv("MIRROR")
SERVER_HTTP_PROXY = os.getenv("SERVER_HTTP_PROXY")
CUSTOM_DOWNLOAD_ENDPOINT = os.getenv("CUSTOM_DOWNLOAD_ENDPOINT")
BUILD_SOURCES = os.getenv("BUILD_SOURCES")
NO_AUTH_REGISTRY = os.getenv("NO_AUTH_REGISTRY")
AUTH_REGISTRY = os.getenv("AUTH_REGISTRY")
CHROMIUM_DEV_TOOLS = os.getenv("REMOTE_DEBUG", "").lower() == "true"
CHROMIUM_DEV_PORT = 9222 + int(os.getenv("TEST_ENV_NUMBER", "0"))

# SCC credentials
SCC_CREDENTIALS = os.getenv("SCC_CREDENTIALS")
scc_credentials_valid = False
if SCC_CREDENTIALS:
    parts = SCC_CREDENTIALS.split("|")
    scc_credentials_valid = len(parts) == 2 and all(parts)

# Custom repositories (Build Validation)
_custom_repos_path = Path(__file__).parent.parent / "features" / "upload_files" / "custom_repositories.json"
CUSTOM_REPOSITORIES = None
BUILD_VALIDATION = False
if _custom_repos_path.exists():
    CUSTOM_REPOSITORIES = json.loads(_custom_repos_path.read_text())
    BUILD_VALIDATION = True
