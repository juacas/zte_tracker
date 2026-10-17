"""Tests for the ZTE E2633 (China Mobile firmware) login and WiFi client reading, against a LOCAL FAKE server.

The fake server only reproduces the flow measured from a browser session (the ``Check`` header and the field
order). It proves the code follows that flow; it does NOT prove a real E2633 accepts it.
Run on its own (Home Assistant is not needed): python3 -m unittest tests/test_e2633_client.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The zte_tracker package __init__ pulls in Home Assistant. Load only the constants zteclient needs.
pkg = types.ModuleType("zte_tracker")
pkg.__path__ = [str(ROOT / "custom_components" / "zte_tracker")]
const = types.ModuleType("zte_tracker.const")
const.DEFAULT_QUERY_ROUTER_DETAILS = True
const.DEFAULT_QUERY_WAN_STATUS = True
sys.modules["zte_tracker"] = pkg
sys.modules["zte_tracker.const"] = const

from zte_tracker.zteclient.zte_client import zteClient  # noqa: E402

PASSWORD = "fake-test-password"
TOKEN = "fake-login-token"
LOGIN_PAGE = '<html><script>addParameter("_sessionTOKEN", "98765");</script><input id="Frm_Password"></html>'
HOME_PAGE = "<html>home</html>"
CLIENTS_DATA = {
    "clientsData": {
        "1": {"MacAddr": "02:00:00:00:00:01", "IpAddr": "192.168.1.10", "HostName": "host-a", "AccessType": "1", "Rssi": "-65", "WirelessMode": "802.11ax", "RxRateBps": "1200", "TxRateBps": "800"},
        "2": {"MacAddr": "02:00:00:00:00:02", "IpAddr": "192.168.1.11", "HostName": "host-b", "AccessType": "2", "Rssi": "-72", "WirelessMode": "802.11ac"},
        "3": {"MacAddr": "not-a-mac", "IpAddr": "192.168.1.12"},
        "MGET_INST_NUM": 3,
    }
}


class FakeZte(BaseHTTPRequestHandler):
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
        srv = self.server
        if self.path == "/":
            return self._send(200, HOME_PAGE if self._has_session() else LOGIN_PAGE)
        if self.path.startswith("/function_module/login_module/login_page/logintoken_lua.lua"):
            return self._send(200, f"<response>{TOKEN}</response>", "text/xml")
        if self.path.startswith("/getpage.lua"):
            if srv.expire_sessions > 0:  # simulate an expired session
                srv.expire_sessions -= 1
                return self._send(200, LOGIN_PAGE)
            if not self._has_session():
                return self._send(200, LOGIN_PAGE)
            action = parse_qs(urlparse(self.path).query).get("Action", [""])[0]
            if action == "GetALLClients":
                return self._send(200, json.dumps(CLIENTS_DATA), "application/json")
            return self._send(404, "")
        self._send(404, "")

    def do_POST(self):
        srv = self.server
        srv.login_count += 1
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        fields = {k: v[0] for k, v in parse_qs(raw.decode()).items()}
        order = list(parse_qs(raw.decode(), keep_blank_values=True).keys())
        ok = (
            fields.get("Username") == "user"
            and fields.get("Password") == hashlib.sha256((PASSWORD + TOKEN).encode()).hexdigest()
            and fields.get("_sessionTOKEN") == "98765"
            and fields.get("action") == "login"
            and order == ["Username", "Password", "action", "Frm_Logintoken", "captchaCode", "_sessionTOKEN"]
            and self.headers.get("Check") == hashlib.sha256(raw).hexdigest()
        )
        if ok:
            return self._send(200, HOME_PAGE, cookie="SID=ok; Path=/")
        self._send(200, LOGIN_PAGE)


class E2633Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeZte)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.server.expire_sessions = 0
        self.server.login_count = 0

    def _client(self, password: str = PASSWORD) -> zteClient:
        return zteClient(
            f"127.0.0.1:{self.server.server_port}", "user", password, "E2633", scheme="http",
        )

    def test_login_and_read_wifi_clients(self):
        c = self._client()
        self.assertTrue(c.login())
        devices = c.get_devices_response()
        self.assertEqual(self.server.login_count, 1)
        self.assertEqual([d["MACAddress"] for d in devices], ["02:00:00:00:00:01", "02:00:00:00:00:02"])
        self.assertTrue(all(d["NetworkType"] == "WLAN" for d in devices))
        self.assertEqual([d["Port"] for d in devices], ["2.4G", "5G"])
        self.assertEqual(devices[0]["HostName"], "host-a")
        self.assertEqual([d["Rssi"] for d in devices], [-65, -72])
        self.assertEqual(devices[1]["WirelessMode"], "802.11ac")
        self.assertEqual((devices[0]["RxRate"], devices[0]["TxRate"]), (1200, 800))

    def test_clients_attribute_shape(self):
        from zte_tracker.zteclient.zte_client import cmcc_wifi_clients
        c = self._client()
        c.login()
        dev = {d["MACAddress"]: {
            "name": d["HostName"], "ip": d["IPAddress"], "active": True, "network_type": d["NetworkType"],
            "port": d["Port"], "rssi": d["Rssi"], "wireless_mode": d["WirelessMode"],
            "rx_rate": d["RxRate"], "tx_rate": d["TxRate"]}
            for d in c.get_devices_response()}
        dev["02:00:00:00:00:99"] = {"name": "old", "ip": "", "active": False, "network_type": "WLAN", "port": "2.4G"}
        dev["02:00:00:00:00:98"] = {"name": "wired", "ip": "", "active": True, "network_type": "LAN", "port": "lan1"}
        clients = cmcc_wifi_clients(dev)
        self.assertEqual(sorted(d["mac"] for d in clients), ["02:00:00:00:00:01", "02:00:00:00:00:02"])
        a = next(d for d in clients if d["mac"] == "02:00:00:00:00:01")
        self.assertEqual(a, {"mac": "02:00:00:00:00:01", "ip": "192.168.1.10", "name": "host-a",
                             "band": "2.4G", "rssi": -65, "mode": "802.11ax", "rx_rate": 1200, "tx_rate": 800})

    def test_wrong_password_is_not_retried_and_not_leaked(self):
        wrong_password = "wrong-password-used-only-in-this-test"
        c = self._client(wrong_password)
        self.assertFalse(c.login())
        self.assertEqual(self.server.login_count, 1)
        self.assertNotIn(wrong_password, c.statusmsg)
        # After a failure the client backs off: the next call sends no further login request.
        self.assertFalse(c.login())
        self.assertEqual(self.server.login_count, 1)

    def test_expired_session_logs_in_again(self):
        c = self._client()
        self.assertTrue(c.login())
        self.assertTrue(c.get_wifi_devices())
        self.server.expire_sessions = 1
        self.assertIsNone(c.get_wifi_devices())
        self.assertIsNone(c.login_data)
        self.assertTrue(c.login())
        self.assertEqual(self.server.login_count, 2)
        self.assertTrue(c.get_wifi_devices())

    def test_logout_keeps_session_and_reboot_wan_unsupported(self):
        c = self._client()
        c.login()
        session = c.session
        c.logout()
        self.assertIs(c.session, session, "E2633 logout must not drop the session")
        self.assertFalse(c.reboot())
        self.assertEqual(c.get_wan_status(), {})
        self.assertEqual(c.get_router_details(), {})
        self.assertEqual(c.get_lan_devices(), [])

    def test_model_is_registered(self):
        self.assertIn("E2633", zteClient.get_models())


if __name__ == "__main__":
    unittest.main()
