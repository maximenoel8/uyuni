import ssl
import xmlrpc.client

from support.env import DEBUG_MODE


class XmlrpcClient:
    def __init__(self, host: str):
        protocol = "http" if DEBUG_MODE else "https"
        url = f"{protocol}://{host}/rpc/api"
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self._client = xmlrpc.client.ServerProxy(url, context=context)

    def call(self, method_name: str, *params):
        """Call an XML-RPC method. Raises RuntimeError on XMLRPC fault."""
        try:
            method = self._client
            for part in method_name.split("."):
                method = getattr(method, part)
            return method(*params)
        except xmlrpc.client.Fault as e:
            raise RuntimeError(
                f"XMLRPC fault calling {method_name}: "
                f"code={e.faultCode} string={e.faultString}") from e
