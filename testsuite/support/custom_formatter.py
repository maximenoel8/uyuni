# Copyright (c) 2024 SUSE LLC.
# Licensed under the terms of the MIT license.

"""
Python port of Ruby's custom_formatter.

Provides FeaturePrependPlugin: a pytest plugin that prepends the feature
file name to each test's headline in the output, mirroring the Ruby
formatter that labels each scenario with its originating feature file.
"""

import pytest


class FeaturePrependPlugin:
    """Prepends feature file name to test output lines."""

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_logreport(self, report):
        yield
        if report.when == "call":
            parts = report.nodeid.split("::")
            if len(parts) > 1:
                feature_name = parts[0].split("/")[-1].replace(".feature", "")
                if report.head_line:
                    report.head_line = f"[{feature_name}] {report.head_line}"
