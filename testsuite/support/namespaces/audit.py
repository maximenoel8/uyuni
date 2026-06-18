# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# Audit namespace


class NamespaceAudit:
    def __init__(self, api_test):
        self._api = api_test

    def list_systems_by_patch_status(self, cve_identifier):
        """Lists the systems that are affected by a given CVE."""
        return self._api.call("audit.listSystemsByPatchStatus", cve_identifier)
