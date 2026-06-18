# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

# API namespace


class NamespaceApi:
    def __init__(self, api_test):
        self._api = api_test

    def get_count_of_api_namespaces(self):
        """Returns the amount of API namespaces."""
        namespaces = self._api.call("api.getApiNamespaces")
        return 0 if namespaces is None else len(namespaces)

    def get_count_of_api_call_list_groups(self):
        """Returns the amount of available API calls."""
        call_list = self._api.call("api.getApiCallList")
        return 0 if call_list is None else len(call_list)

    def get_count_of_api_namespace_call_list(self):
        """Returns the count of the number of API calls in the API namespace call list."""
        count = 0
        namespaces = self._api.call("api.getApiNamespaces")
        if namespaces:
            for ns in namespaces:
                call_list = self._api.call("api.getApiNamespaceCallList", ns[0])
                if call_list is not None:
                    count += len(call_list)
        return count
