import ipaddress
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

zteClient = _load_client()


class FakeGoformResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.request = None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeGoformSession:
    def __init__(self, get_routes=None, post_routes=None):
        self.get_routes = get_routes or {}
        self.post_routes = post_routes or {}
        self.headers = {}
        self.cookies = {}
        self.trust_env = True
        self.get_calls = []
        self.post_calls = []

    def get(self, url, verify=False, timeout=10, **kwargs):
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        cmd = (qs.get("cmd") or [""])[0]
        self.get_calls.append((url, cmd))
        handler = self.get_routes.get(cmd)
        if callable(handler):
            return FakeGoformResponse(handler(cmd))
        if handler is not None:
            return FakeGoformResponse(handler)
        return FakeGoformResponse({})

    def post(self, url, data=None, verify=False, timeout=10, **kwargs):
        payload = dict(data or {})
        goform_id = payload.get("goformId", "")
        self.post_calls.append((url, payload))
        handler = self.post_routes.get(goform_id)
        if callable(handler):
            return FakeGoformResponse(handler(payload))
        if handler is not None:
            return FakeGoformResponse(handler)
        return FakeGoformResponse({"result": "0"})

    def close(self):
        self.cookies.clear()


class TestG5BProfile(unittest.TestCase):
    def setUp(self):
        self.client = zteClient("192.168.0.1", "admin", "password", "G5B")

    def test_g5b_registered_in_models_and_profiles(self):
        self.assertIn("G5B", zteClient.get_models())
        profiles = zteClient.get_profiles()
        self.assertIn("G5B", profiles)
        self.assertEqual(profiles["G5B"].get("api_type"), "goform")
        self.assertTrue(profiles["G5B"].get("cellular_metrics"))

    def test_setup_session_configures_goform_headers(self):
        self.client._setup_session()
        self.assertFalse(self.client.session.trust_env)
        self.assertEqual(
            self.client.session.headers.get("X-Requested-With"),
            "XMLHttpRequest",
        )
        self.assertEqual(
            self.client.session.headers.get("Referer"),
            "https://192.168.0.1/index.html",
        )

    def test_login_success_and_session_reuse(self):
        session = FakeGoformSession(
            get_routes={
                "Language,cr_version,wa_inner_version": {
                    "Language": "en",
                    "wa_inner_version": "BD_STD_G5BV1.0.0B08",
                    "cr_version": "CR_LIU2G5BV1.0.0B07",
                },
                "LD": {
                    "LD": "4319324bf756c699f4bd3dd83ed3f16bd30d2122d10a25a8f6f2617d63360d42"
                },
                "loginfo": {"loginfo": "ok"},
            },
            post_routes={
                "LOGIN": {"result": "0"},
            },
        )
        self.client.session = session

        self.assertTrue(self.client.login())
        self.assertEqual(len(session.post_calls), 1)
        _, post_data = session.post_calls[0]
        self.assertEqual(post_data["goformId"], "LOGIN")
        self.assertEqual(post_data["user"], "admin")
        expected_pwd = zteClient._sha256_upper(
            zteClient._sha256_upper("password")
            + "4319324bf756c699f4bd3dd83ed3f16bd30d2122d10a25a8f6f2617d63360d42"
        )
        self.assertEqual(post_data["password"], expected_pwd)

        # Second login reuses active session when loginfo == "ok"
        self.assertTrue(self.client.login())
        self.assertEqual(len(session.post_calls), 1)

    def test_login_bad_password_and_lockout(self):
        session = FakeGoformSession(
            get_routes={
                "Language,cr_version,wa_inner_version": {
                    "wa_inner_version": "BD_STD_G5BV1.0.0B08",
                    "cr_version": "CR_LIU2G5BV1.0.0B07",
                },
                "LD": {"LD": "abcd"},
                "psw_fail_num_str,login_lock_time": {
                    "psw_fail_num_str": "4",
                    "login_lock_time": "0",
                },
            },
            post_routes={
                "LOGIN": {"result": "3"},
            },
        )
        self.client.session = session
        self.assertFalse(self.client.login())
        self.assertEqual(self.client.statusmsg, "Login denied: Bad password")

        # Lockout
        session.get_routes["psw_fail_num_str,login_lock_time"] = {
            "psw_fail_num_str": "0",
            "login_lock_time": "120",
        }
        self.assertFalse(self.client.login())
        self.assertIn("locked for 120 seconds", self.client.statusmsg)

    def test_logout_and_reboot_compute_ad_token(self):
        session = FakeGoformSession(
            get_routes={
                "Language,cr_version,wa_inner_version": {
                    "wa_inner_version": "BD_STD_G5BV1.0.0B08",
                    "cr_version": "CR_LIU2G5BV1.0.0B07",
                },
                "LD": {"LD": "abcd"},
                "RD": {"RD": "19572ba72a82ac203dc815c3a8a0ec22"},
                "loginfo": {"loginfo": "ok"},
            },
            post_routes={
                "LOGIN": {"result": "0"},
                "REBOOT_DEVICE": {"result": "success"},
                "LOGOUT": {"result": "success"},
            },
        )
        self.client.session = session
        expected_ad = zteClient._sha256_upper(
            zteClient._sha256_upper("BD_STD_G5BV1.0.0B08CR_LIU2G5BV1.0.0B07")
            + "19572ba72a82ac203dc815c3a8a0ec22"
        )

        # reboot() logs in, posts REBOOT_DEVICE, and logs out in finally
        self.assertTrue(self.client.reboot())
        self.assertEqual(len(session.post_calls), 3)
        self.assertEqual(session.post_calls[0][1]["goformId"], "LOGIN")
        self.assertEqual(session.post_calls[1][1]["goformId"], "REBOOT_DEVICE")
        self.assertEqual(session.post_calls[1][1]["AD"], expected_ad)
        self.assertEqual(session.post_calls[2][1]["goformId"], "LOGOUT")
        self.assertEqual(session.post_calls[2][1]["AD"], expected_ad)

    def test_lan_and_wifi_devices_parsing(self):
        session = FakeGoformSession(
            get_routes={
                "lan_station_list": {
                    "lan_station_list": [
                        {
                            "mac_addr": "bc:24:11:aa:bb:cc",
                            "ip_addr": "192.168.0.10",
                            "hostname": "--",
                            "connect_time": "3600",
                        }
                    ]
                },
                "station_list": {
                    "station_list": [
                        {
                            "mac_addr": "34:6f:24:11:22:33",
                            "ip_addr": "192.168.0.125",
                            "hostname": "LivingRoomPlug",
                            "connect_time": "1736884128",
                            "interfacetype": "WIFI1",
                        },
                        {
                            "mac_addr": "90:09:df:44:55:66",
                            "ip_addr": "192.168.0.219",
                            "hostname": "--",
                            "connect_time": "1736884200",
                            "interfacetype": "WIFI6",
                        },
                    ]
                },
                "hostNameList": {
                    "hostNameList": "bc:24:11:aa:bb:cc,ProxmoxServer;90:09:df:44:55:66,--;",
                },
            }
        )
        self.client.session = session

        lan_devices = self.client.get_lan_devices()
        self.assertEqual(len(lan_devices), 1)
        self.assertEqual(lan_devices[0]["HostName"], "ProxmoxServer")
        self.assertEqual(lan_devices[0]["IPAddress"], "192.168.0.10")
        self.assertEqual(lan_devices[0]["MACAddress"], "BC:24:11:AA:BB:CC")
        self.assertEqual(lan_devices[0]["Port"], "LAN")
        self.assertEqual(lan_devices[0]["NetworkType"], "LAN")

        wifi_devices = self.client.get_wifi_devices()
        self.assertEqual(len(wifi_devices), 2)
        self.assertEqual(wifi_devices[0]["HostName"], "LivingRoomPlug")
        self.assertEqual(wifi_devices[0]["NetworkType"], "WLAN")
        self.assertEqual(wifi_devices[0]["Port"], "2.4GHz")
        self.assertEqual(wifi_devices[1]["HostName"], "")
        self.assertEqual(wifi_devices[1]["NetworkType"], "WLAN")
        self.assertEqual(wifi_devices[1]["Port"], "5GHz")

    def test_router_details_and_wan_cellular_metrics(self):
        wan_payload = {
            "loginfo": "ok",
            "ppp_status": "ipv4_ipv6_connected",
            "wan_ipaddr": "198.51.100.42",
            "ipv6_wan_ipaddr": "2001:db8:1234:5678::1/64",
            "opms_wan_mode": "PPP",
            "flux_realtime_time": "22464",
            "flux_monthly_rx_bytes": "5734321102",
            "flux_monthly_tx_bytes": "597368020",
            "flux_realtime_rx_thrpt": "981",
            "flux_realtime_tx_thrpt": "628",
            "network_type": "ENDC",
            "network_provider_fullname": "3",
            "rplmn_num": "27202",
            "network_simcard_roam": "Home",
            "network_signalbar": "5",
            "wan_lte_ca": "ca_activated",
            "network_cell_id": "137b2c",
            "lte_pci": "153",
            "wan_active_band": "LTE BAND 3",
            "wan_active_channel": "1275",
            "bandwidth": "20.0MHz",
            "network_lte_rsrp": "-87",
            "lte_rsrq": "-9",
            "network_sinr": "10.8",
            "lte_rssi": "-57",
            "network_lte_ca_scell_info": "0,210,2,1,300,15.0;",
            "lte_multi_ca_scell_sig_info": "-92,-10,8.5,-65,1;",
            "network_Z5g_CELL_ID": "2a4b6c",
            "network_Z5g_PCI": "18f",
            "nr5g_action_band": "n78",
            "nr5g_action_channel": "641664",
            "nr5g_nsa_bandwidth": "100MHz",
            "Z5g_rsrp": "-87",
            "Z5g_rsrq": "-11",
            "Z5g_SINR": "18.5",
            "Z5g_rssi": "-75",
            "nr_multi_ca_scell_info": "0,400,2,n78,635000,40MHz,1,-90,-12,15.0,-78;",
        }

        def get_handler(cmd):
            if cmd == "hardware_version,wa_inner_version,web_version,system_uptime":
                return {
                    "hardware_version": "G5B_HW1.0",
                    "wa_inner_version": "BD_STD_G5BV1.0.0B08",
                    "web_version": "WEB_STD_G5BV1.0.0B07",
                    "system_uptime": "23850",
                }
            return wan_payload

        session = FakeGoformSession()
        session.get = lambda url, verify=False, timeout=10, **kw: FakeGoformResponse(
            get_handler((parse_qs(urlparse(url).query).get("cmd") or [""])[0])
        )
        self.client.session = session

        details = self.client.get_router_details()
        self.assertEqual(details["ModelName"], "G5B")
        self.assertEqual(details["ManuFacturer"], "ZTE")
        self.assertEqual(details["HardwareVer"], "G5B_HW1.0")
        self.assertEqual(details["SoftwareVer"], "BD_STD_G5BV1.0.0B08")
        self.assertEqual(details["PowerOnTime"], 23850)

        wan = self.client.get_wan_status()
        self.assertTrue(wan["WAN_connected"])
        self.assertRegex(wan["WAN_public_ip"], r"^\d{1,3}(?:\.\d{1,3}){3}$")
        self.assertIsInstance(
            ipaddress.ip_address(wan["WAN_public_ip"]), ipaddress.IPv4Address
        )
        self.assertRegex(wan["WAN_ipv6_ip"], r"^[0-9a-fA-F:]+(?:/\d{1,3})?$")
        self.assertIsInstance(
            ipaddress.ip_interface(wan["WAN_ipv6_ip"]), ipaddress.IPv6Interface
        )
        self.assertEqual(wan["WAN_mode"], "PPP")
        self.assertEqual(wan["WAN_uptime"], 22464)
        self.assertEqual(wan["WAN_rx_bytes"], 5734321102)
        self.assertEqual(wan["WAN_tx_bytes"], 597368020)

        # Cellular general metrics
        self.assertEqual(wan["cellular_network_type"], "ENDC")
        self.assertEqual(wan["cellular_operator"], "3")
        self.assertEqual(wan["cellular_plmn"], "27202")
        self.assertEqual(wan["cellular_signal_bars"], 5)
        self.assertEqual(wan["cellular_ca_status"], "ca_activated")

        # LTE metrics
        self.assertEqual(wan["lte_cell_id"], 1276716)
        self.assertEqual(wan["lte_cell_id_hex"], "137b2c")
        self.assertEqual(wan["lte_pci"], 339)
        self.assertEqual(wan["lte_band"], "LTE BAND 3")
        self.assertEqual(wan["lte_earfcn"], 1275)
        self.assertEqual(wan["lte_bandwidth"], "20.0MHz")
        self.assertEqual(wan["lte_rsrp_dbm"], -87.0)
        self.assertEqual(wan["lte_rsrq_db"], -9.0)
        self.assertEqual(wan["lte_sinr_db"], 10.8)
        self.assertEqual(wan["lte_rssi_dbm"], -57.0)
        self.assertEqual(len(wan["lte_cells"]), 2)
        self.assertEqual(wan["lte_cells"][0]["id"], "PCC")
        self.assertEqual(wan["lte_cells"][1]["id"], "SCC0")
        self.assertEqual(wan["lte_cells"][1]["band"], "Band1")

        # 5G NR metrics
        self.assertEqual(wan["nr5g_cell_id"], 2771820)
        self.assertEqual(wan["nr5g_cell_id_hex"], "2a4b6c")
        self.assertEqual(wan["nr5g_pci"], 399)
        self.assertEqual(wan["nr5g_band"], "N78")
        self.assertEqual(wan["nr5g_arfcn"], 641664)
        self.assertEqual(wan["nr5g_bandwidth"], "100MHz")
        self.assertEqual(wan["nr5g_rsrp_dbm"], -87.0)
        self.assertEqual(wan["nr5g_rsrq_db"], -11.0)
        self.assertEqual(wan["nr5g_sinr_db"], 18.5)
        self.assertEqual(wan["nr5g_rssi_dbm"], -75.0)
        self.assertEqual(len(wan["nr5g_cells"]), 2)
        self.assertEqual(wan["nr5g_cells"][0]["id"], "PCC")
        self.assertEqual(wan["nr5g_cells"][1]["id"], "SCC0")
        self.assertEqual(wan["nr5g_cells"][1]["dl_bandwidth"], "40MHz")


if __name__ == "__main__":
    unittest.main()
