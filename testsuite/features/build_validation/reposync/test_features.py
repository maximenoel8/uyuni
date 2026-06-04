# Copyright (c) 2026 SUSE LLC
# Licensed under the terms of the MIT license.

"""Bind all .feature files in this directory to pytest-bdd for collection."""

from pytest_bdd import scenarios

scenarios(".")
