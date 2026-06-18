import re

from support.env import DEFAULT_TIMEOUT


class HttpClient:
    _GET_PREFIXES = ("list", "get", "is", "find")
    _GET_PATTERNS = (
        re.compile(r"^system\.search\."),
        re.compile(r"^packages\.search\."),
        re.compile(r"^auth\.logout$"),
        re.compile(r"^errata\.applicableToChannels$"),
    )

    def __init__(self, host: str, ssl_verify: bool = False):
        try:
            import httpx
            self._client = httpx.Client(
                base_url=f"https://{host}",
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT,
            )
        except ImportError:
            self._client = None
        self._session_cookie = None

    def call(self, method_name: str, *params):
        """Call an API method via HTTP."""
        if self._client is None:
            raise RuntimeError("httpx not installed — HTTP client unavailable")
        http_method, url, data = self._prepare_call(method_name, params)
        headers = {}
        if self._session_cookie:
            headers["Cookie"] = self._session_cookie

        if http_method == "GET":
            resp = self._client.get(url, params=data, headers=headers)
        else:
            resp = self._client.post(url, json=data, headers=headers)

        resp.raise_for_status()

        if "set-cookie" in resp.headers:
            self._session_cookie = resp.headers["set-cookie"]

        if method_name == "auth.login":
            return self._session_cookie

        body = resp.json()
        return body.get("result", body)

    def _prepare_call(self, method_name: str, params: tuple):
        parts = method_name.split(".")
        url = f"/rhn/manager/api/{'/'.join(parts)}"

        is_get = any(method_name.startswith(p) for p in self._GET_PREFIXES)
        if not is_get:
            is_get = any(pat.match(method_name) for pat in self._GET_PATTERNS)

        if is_get:
            flat_params = {f"param{i}": p for i, p in enumerate(params)}
            return "GET", url, flat_params
        return "POST", url, list(params)
