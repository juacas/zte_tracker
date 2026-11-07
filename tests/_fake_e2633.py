"""Local fake of the ZTE E2633 (China Mobile firmware) web UI, for tests only.

It reproduces the login flow measured from a browser session (field order and the
``Check`` header) and the ``GetALLClients`` data page. It proves the client follows
that flow; it does NOT prove a real E2633 accepts it.

Fake credentials only. Bind to 127.0.0.1 and use the ``socket_enabled`` fixture
(pytest-socket blocks sockets in this repo's test run otherwise).
"""

from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

USERNAME = "user"
PASSWORD = "fake-test-password"
LOGIN_TOKEN = "fake-login-token"
SESSION_TOKEN = "98765"
LOGIN_PAGE = (
    '<html><script>addParameter("_sessionTOKEN", "98765");</script>'
    '<input id="Frm_Password"></html>'
)
HOME_PAGE = "<html>home</html>"
CLIENTS_DATA = {
    "clientsData": {
        "1": {
            "MacAddr": "02:00:00:00:00:01",
            "IpAddr": "192.0.2.10",
            "HostName": "host-a",
            "AccessType": "1",
            "Rssi": "-65",
            "WirelessMode": "802.11ax",
            "RxRateBps": "1200",
            "TxRateBps": "800",
        },
        "2": {
            "MacAddr": "02:00:00:00:00:02",
            "IpAddr": "192.0.2.11",
            "HostName": "host-b",
            "AccessType": "2",
            "Rssi": "-72",
            "WirelessMode": "802.11ac",
        },
        "3": {"MacAddr": "not-a-mac", "IpAddr": "192.0.2.12"},
        "MGET_INST_NUM": 3,
    }
}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silent
        pass

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8", cookie: str | None = None):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def _has_session(self) -> bool:
        return "SID=ok" in (self.headers.get("Cookie") or "")

    def do_GET(self):
        state = self.server.state
        if self.path == "/":
            if state.home_status != 200:
                return self._send(state.home_status, "unavailable")
            return self._send(200, HOME_PAGE if self._has_session() else LOGIN_PAGE)
        if self.path.startswith("/function_module/login_module/login_page/logintoken_lua.lua"):
            if state.token_status != 200:
                return self._send(state.token_status, "unavailable")
            return self._send(200, f"<response>{LOGIN_TOKEN}</response>", "text/xml")
        if self.path.startswith("/getpage.lua"):
            state.data_requests += 1
            if state.data_status != 200:
                return self._send(state.data_status, "unavailable")
            if state.expire_sessions > 0:  # simulate an expired session
                state.expire_sessions -= 1
                return self._send(200, LOGIN_PAGE)
            if not self._has_session():
                return self._send(200, LOGIN_PAGE)
            action = parse_qs(urlparse(self.path).query).get("Action", [""])[0]
            if action == "GetALLClients":
                return self._send(200, json.dumps(state.clients), "application/json")
            return self._send(404, "")
        self._send(404, "")

    def do_POST(self):
        state = self.server.state
        state.login_count += 1
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        fields = {k: v[0] for k, v in parse_qs(raw.decode()).items()}
        order = list(parse_qs(raw.decode(), keep_blank_values=True).keys())
        ok = (
            fields.get("Username") == USERNAME
            and fields.get("Password") == hashlib.sha256((PASSWORD + LOGIN_TOKEN).encode()).hexdigest()
            and fields.get("_sessionTOKEN") == SESSION_TOKEN
            and fields.get("action") == "login"
            and order == ["Username", "Password", "action", "Frm_Logintoken", "captchaCode", "_sessionTOKEN"]
            and self.headers.get("Check") == hashlib.sha256(raw).hexdigest()
        )
        if ok:
            return self._send(200, HOME_PAGE, cookie="SID=ok; Path=/")
        self._send(200, LOGIN_PAGE)


class FakeE2633:
    """A fake router on 127.0.0.1 with switches the tests can flip at any time."""

    def __init__(self) -> None:
        self.expire_sessions = 0  # next N data reads answer with the login page
        self.login_count = 0  # login POSTs received
        self.data_requests = 0  # data page GETs received
        self.home_status = 200  # HTTP status of GET /
        self.token_status = 200  # HTTP status of the login token page
        self.data_status = 200  # HTTP status of the data page
        self.clients = CLIENTS_DATA
        self.port = 0
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.port}"

    def start(self) -> None:
        """Start listening (on the same port again after ``stop``)."""
        self._server = HTTPServer(("127.0.0.1", self.port), _Handler)
        self._server.state = self
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening: connections to the port are refused, like a router that is off."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._server = None
