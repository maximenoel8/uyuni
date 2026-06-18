# Copyright (c) 2026 SUSE LLC
# Licensed under the terms of the MIT license.

"""
Entry point for running the full testsuite.

Each feature directory has its own test_features.py that calls scenarios(".").
This file exists so that `pytest` (no args) from the testsuite root still works
by letting pytest discover the per-directory files recursively.

To run a specific subset, point pytest at the directory:

    pytest features/core/ -v
    pytest features/secondary/ -v

To run a single feature file, filter by its stem name:

    pytest features/core/ -k "srv_first_settings" -v

To run the full suite:

    pytest features/ -v
    # or simply:
    pytest -v
"""
