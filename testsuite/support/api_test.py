# Copyright (c) 2022-2025 SUSE LLC.
# Licensed under the terms of the MIT license.

import threading
from datetime import datetime, timezone


class ApiTest:
    def __init__(self, connection):
        self._connection = connection
        self._lock = threading.Lock()
        self._session_key = None
        self._log_file = open("api.log", "a")
        import os
        self.current_user = os.getenv("MANAGER_USER", "admin")
        self.current_password = os.getenv("MANAGER_PASSWORD", "admin")

        from support.namespaces.actionchain import NamespaceActionChain
        from support.namespaces.activationkey import NamespaceActivationKey
        from support.namespaces.api import NamespaceApi
        from support.namespaces.audit import NamespaceAudit
        from support.namespaces.channel import NamespaceChannel
        from support.namespaces.configchannel import NamespaceConfigChannel
        from support.namespaces.image import NamespaceImage
        from support.namespaces.kickstart import NamespaceKickstart
        from support.namespaces.schedule import NamespaceSchedule
        from support.namespaces.system import NamespaceSystem
        from support.namespaces.user import NamespaceUser

        self.actionchain = NamespaceActionChain(self)
        self.activationkey = NamespaceActivationKey(self)
        self.api = NamespaceApi(self)
        self.audit = NamespaceAudit(self)
        self.channel = NamespaceChannel(self)
        self.configchannel = NamespaceConfigChannel(self)
        self.image = NamespaceImage(self)
        self.kickstart = NamespaceKickstart(self)
        self.schedule = NamespaceSchedule(self)
        self.system = NamespaceSystem(self)
        self.user = NamespaceUser(self)

    def call(self, method_name: str, *params):
        """Thread-safe API call with automatic session management."""
        with self._lock:
            if self._session_key is None:
                self._login()
            self._log(method_name, params)
            return self._connection.call(method_name, self._session_key, *params)

    def _login(self):
        self._session_key = self._connection.call(
            "auth.login", self.current_user, self.current_password)

    def logout(self):
        if self._session_key:
            try:
                self._connection.call("auth.logout", self._session_key)
            except Exception:
                pass
            self._session_key = None

    def _log(self, method_name: str, params: tuple):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._log_file.write(f"[{ts}] {method_name}({params})\n")
        self._log_file.flush()

    def date_now(self):
        raise NotImplementedError

    def is_date(self, value) -> bool:
        raise NotImplementedError


class ApiTestXmlrpc(ApiTest):
    def __init__(self, host: str):
        from support.xmlrpc_client import XmlrpcClient
        super().__init__(XmlrpcClient(host))

    def date_now(self):
        import xmlrpc.client
        return xmlrpc.client.DateTime(datetime.now(timezone.utc))

    def is_date(self, value) -> bool:
        import xmlrpc.client
        return isinstance(value, xmlrpc.client.DateTime)


class ApiTestHttp(ApiTest):
    def __init__(self, host: str):
        from support.http_client import HttpClient
        super().__init__(HttpClient(host))

    def date_now(self):
        return datetime.now(timezone.utc).isoformat()

    def is_date(self, value) -> bool:
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
                return True
            except ValueError:
                return False
        return False


def new_api_client() -> ApiTest:
    """Factory: XMLRPC by default, HTTP if API_PROTOCOL=http."""
    from support.env import SERVER, API_PROTOCOL
    if API_PROTOCOL == "http":
        return ApiTestHttp(SERVER)
    return ApiTestXmlrpc(SERVER)
