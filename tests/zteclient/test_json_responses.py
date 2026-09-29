"""JSON responses from F6745Q-style firmware (#106), shaped after the reporter's support bundle."""

import json
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

# Node names in the bundle are hidden; these are deliberately unlike the XML profile names.
LAN_JSON = json.dumps(
    {
        "Device.Hosts": {
            "Instance": [
                {
                    "path": "DEV.HOST.1",
                    "parameters": {
                        "IPAddress": "192.168.1.10",
                        "PhysAddress": "aa:bb:cc:dd:ee:01",
                        "HostName": "laptop",
                        "Active": 1,
                        "Layer1Interface": "LAN1",
                    },
                },
                {
                    "path": "DEV.HOST.2",
                    "parameters": {
                        "IPAddress": "192.168.1.11",
                        "PhysAddress": "aa:bb:cc:dd:ee:02",
                        "HostName": None,
                        "Active": 0,
                    },
                },
                {"path": "DEV.HOST.3", "parameters": {"HostName": "no-mac"}},
            ]
        },
        "IF_ERRORID": 0,
        "IF_ERRORTYPE": 200,
        "IF_ERRORSTR": "SUCC",
        "IF_ERRORPARAM": "",
    }
)

WLAN_JSON = json.dumps(
    {
        "Device.WiFi.Clients": {
            "Instance": [
                {
                    "path": "DEV.WIFI.AP1.AD1",
                    "parameters": {
                        "SSID": "home",
                        "HostName": "phone",
                        "SignalStrength": -55,
                        "IPAddress": "192.168.1.20",
                        "MACAddress": "aa:bb:cc:dd:ee:03",
                    },
                }
            ]
        },
        "IF_ERRORSTR": "SUCC",
    }
)

DEVINFO_JSON = json.dumps(
    {
        "IF_ERRORSTR": "SUCC",
        "Device.DeviceInfo": {
            "Instance": [
                {
                    "path": "DEV.INFO",
                    "parameters": {
                        "Manufacturer": "ZTE",
                        "SerialNumber": "ZTEXX00000000",
                        "UpTime": 45005,
                        "ModelName": "F6745Q",
                        "HardwareVersion": "V1.0",
                        "SoftwareVersion": "ZTEGF674510MA",
                        "ManufacturerOUI": 1234,
                    },
                }
            ]
        },
    }
)

WAN_JSON = json.dumps(
    {
        "Device.WAN.1": {
            "Instance": {
                "path": "WAN1",
                "parameters": {
                    "WANCName": "WAN_internet",
                    "ConnStatus": "Connected",
                    "UpTime": 600,
                    "IPAddress": "203.0.113.5",
                },
            }
        },
        "IF_ERRORSTR": "SUCC",
    }
)

# The only WAN fields the bundle shows: none of them map to a status attribute.
WAN_JSON_UNKNOWN = json.dumps(
    {
        "Device.WAN.1": {
            "Instance": [
                {
                    "path": "WAN1",
                    "parameters": {
                        "Alias": "wan",
                        "IPv4Mode": "dhcp",
                        "IPv6Mode": "off",
                    },
                }
            ]
        },
        "IF_ERRORSTR": "SUCC",
    }
)

# Reporter's wan_internetstatus_lua.lua (#106), addresses replaced.
WAN_JSON_TR181 = json.dumps(
    {
        "DHCPv6.": {"Instance": []},
        "IF_ERRORID": 0,
        "DHCPv4.": {
            "Instance": [
                {
                    "parameters": {
                        "IPMode": "DHCP",
                        "RemoteGateway": "10.224.0.1",
                        "MACAddress": "aa:bb:cc:dd:ee:10",
                        "IPAddress": "10.224.0.2",
                        "DNSServers": "",
                        "Alias": "VOIX",
                        "IPVersion": "IPv4",
                    },
                    "path": "DEV.IP.IF2",
                }
            ]
        },
        "PPP6.": {
            "Instance": [
                {
                    "parameters": {
                        "IPMode": "PPP",
                        "GUA": "",
                        "LLA": "",
                        "MACAddress": "aa:bb:cc:dd:ee:11",
                        "ConnectionStatus": "Unconfigured",
                        "DNSServersv6": "",
                        "Alias": "INTERNET",
                        "IPVersion": "IPv6",
                    },
                    "path": "DEV.PPP.IF1",
                }
            ]
        },
        "PPP4.": {
            "Instance": [
                {
                    "parameters": {
                        "IPMode": "PPP",
                        "ConnectionStatus": "Connected",
                        "MACAddress": "aa:bb:cc:dd:ee:11",
                        "IPAddress": "203.0.113.7",
                        "DNSServers": "198.51.100.1,198.51.100.2",
                        "Alias": "INTERNET",
                        "IPVersion": "IPv4",
                    },
                    "path": "DEV.PPP.IF1",
                }
            ]
        },
        "WANManager.WAN.": {
            "Instance": [
                {
                    "path": "DEV.WAN.1",
                    "parameters": {
                        "Alias": "INTERNET",
                        "IPv6Mode": "none",
                        "IPv4Mode": "ppp4",
                    },
                }
            ]
        },
        "IF_ERRORPARAM": "SUCC",
        "IF_ERRORSTR": "SUCC",
        "IF_ERRORTYPE": 200,
    }
)

# Reporter's optical_info_lua.lua (#106): still XML on this firmware.
OPTICAL_XML = (
    "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
    "<OBJ_LOS_INFO_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>LosInfo</ParaName><ParaValue>0</ParaValue></Instance></OBJ_LOS_INFO_ID>"
    "<OBJ_GPONREGSTATUS_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>RegStatus</ParaName><ParaValue>5</ParaValue></Instance></OBJ_GPONREGSTATUS_ID>"
    "<OBJ_PON_OPTICALPARA_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>Temp</ParaName><ParaValue>53.421</ParaValue>"
    "<ParaName>RxPower</ParaName><ParaValue>-24.5593</ParaValue>"
    "<ParaName>TxPower</ParaName><ParaValue>2.629</ParaValue>"
    "</Instance></OBJ_PON_OPTICALPARA_ID></ajax_response_xml_root>"
)

TIMEOUT_JSON = json.dumps({"IF_ERRORSTR": "SessionTimeout", "IF_ERRORTYPE": 200})


def _response(text=""):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    r.content = text.encode()
    return r


class TestParseResponse(TestCase):
    def setUp(self):
        self.cls = _load_client()

    def test_xml_passes_through(self):
        xml = "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR></ajax_response_xml_root>"
        for body in (xml, xml.encode(), "\n  " + xml):
            root = self.cls._parse_response(body)
            self.assertIsNone(root.get("format"))
            self.assertEqual(root.findtext("IF_ERRORSTR"), "SUCC")

    def test_json_becomes_the_xml_shape(self):
        root = self.cls._parse_response(LAN_JSON.encode())
        self.assertEqual(root.tag, "ajax_response_xml_root")
        self.assertEqual(root.get("format"), "json")
        self.assertEqual(root.findtext("IF_ERRORSTR"), "SUCC")
        self.assertEqual(root.findtext("IF_ERRORTYPE"), "200")
        inst = root.find("Device.Hosts/Instance")
        parsed = self.cls._parse_instance(inst, coerce_numeric=False)
        self.assertEqual(parsed["PhysAddress"], "aa:bb:cc:dd:ee:01")
        self.assertEqual(parsed["Active"], "1")
        self.assertNotIn("_InstID", parsed)

    def test_single_instance_flat_record_and_odd_values(self):
        body = json.dumps(
            {
                "N": {"Instance": {"MACAddress": "x", "nested": {"a": 1}}},
                "L": [1, 2],
                "Z": None,
                "Bad": {"Instance": ["not a record"]},
                "NoInst": {"foo": "bar"},
            }
        )
        root = self.cls._parse_response(body)
        parsed = self.cls._parse_instance(root.find("N/Instance"))
        self.assertEqual(parsed, {"MACAddress": "x"})
        self.assertIsNone(root.findtext("L") or None)
        self.assertEqual(root.findall("Bad/Instance"), [])

    def test_non_object_json_is_an_empty_root(self):
        root = self.cls._parse_response("[1, 2]")
        self.assertEqual(root.get("format"), "json")
        self.assertEqual(len(root), 0)

    def test_malformed_json_raises(self):
        with self.assertRaises(ValueError):
            self.cls._parse_response("{not json")


class TestJsonDevices(TestCase):
    def setUp(self):
        self.client = _load_client()("192.168.1.1", "admin", "pw", "F6745Q")
        self.client.session = MagicMock()

    def test_lan_devices(self):
        self.client.session.get.side_effect = [_response(), _response(LAN_JSON)]
        devices = self.client.get_lan_devices()
        self.assertEqual(len(devices), 2)
        first, second = devices
        self.assertEqual(first["MACAddress"], "AA:BB:CC:DD:EE:01")
        self.assertEqual(first["IPAddress"], "192.168.1.10")
        self.assertEqual(first["HostName"], "laptop")
        self.assertEqual(first["Port"], "LAN1")
        self.assertTrue(first["Active"])
        self.assertEqual(first["NetworkType"], "LAN")
        self.assertFalse(second["Active"])
        self.assertEqual(second["HostName"], "")

    def test_wifi_devices(self):
        self.client.session.get.side_effect = [_response(WLAN_JSON)]
        (device,) = self.client.get_wifi_devices()
        self.assertEqual(device["MACAddress"], "AA:BB:CC:DD:EE:03")
        self.assertEqual(device["Port"], "home")
        self.assertEqual(device["NetworkType"], "WLAN")

    def test_setup_check_gets_devices(self):
        self.client.session.get.side_effect = [
            _response(),
            _response(LAN_JSON),
            _response(WLAN_JSON),
        ]
        self.assertEqual(len(self.client.get_devices_response()), 3)

    def test_router_error_in_json(self):
        with self.assertRaises(Exception):
            self.client.parse_devices(TIMEOUT_JSON, "OBJ_ACCESSDEV_ID", "LAN")

    def test_xml_node_name_still_wins(self):
        xml = """<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
          <OBJ_ACCESSDEV_ID><Instance>
            <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:09</ParaValue>
            <ParaName>AliasName</ParaName><ParaValue>LAN2</ParaValue>
            <ParaName>Layer1Interface</ParaName><ParaValue>ignored</ParaValue>
          </Instance></OBJ_ACCESSDEV_ID>
          <OBJ_OTHER_ID><Instance>
            <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:10</ParaValue>
          </Instance></OBJ_OTHER_ID></ajax_response_xml_root>"""
        (device,) = self.client.parse_devices(xml, "OBJ_ACCESSDEV_ID", "LAN")
        self.assertEqual(device["Port"], "LAN2")

    def test_xml_port_is_unchanged_without_aliasname(self):
        xml = """<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
          <OBJ_ACCESSDEV_ID><Instance>
            <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:09</ParaValue>
            <ParaName>SSID</ParaName><ParaValue>home</ParaValue>
          </Instance></OBJ_ACCESSDEV_ID></ajax_response_xml_root>"""
        (device,) = self.client.parse_devices(xml, "OBJ_ACCESSDEV_ID", "WLAN")
        self.assertEqual(device["Port"], "")

    def test_xml_physaddress_is_not_a_mac(self):
        xml = """<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
          <OBJ_ACCESSDEV_ID><Instance>
            <ParaName>PhysAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:09</ParaValue>
          </Instance></OBJ_ACCESSDEV_ID></ajax_response_xml_root>"""
        self.assertEqual(self.client.parse_devices(xml, "OBJ_ACCESSDEV_ID", "LAN"), [])


class TestJsonRouterDetails(TestCase):
    def test_json_device_info(self):
        client = _load_client()("192.168.1.1", "admin", "pw", "F6745Q")
        client.session = MagicMock()
        client.session.get.side_effect = [_response(), _response(DEVINFO_JSON)]
        details = client.get_router_details()
        self.assertEqual(details["ModelName"], "F6745Q")
        self.assertEqual(details["HardwareVer"], "V1.0")
        self.assertEqual(details["SoftwareVer"], "ZTEGF674510MA")
        self.assertEqual(details["ManuFacturer"], "ZTE")
        self.assertEqual(details["PowerOnTime"], 45005)
        self.assertNotIn("SerialNumber", details)


class TestJsonWanStatus(TestCase):
    def setUp(self):
        self.client = _load_client()("192.168.1.1", "admin", "pw", "F6745Q")
        self.client.session = MagicMock()

    def test_known_fields_are_mapped(self):
        self.client.session.get.side_effect = [_response(), _response(WAN_JSON)]
        wan = self.client.get_wan_status()
        self.assertTrue(wan["WAN_connected"])
        self.assertEqual(wan["WAN_uptime"], 600)
        self.assertEqual(wan["WAN_public_ip"], "203.0.113.5")
        self.assertNotIn("WAN_status_error", wan)

    def test_unknown_fields_are_reported_not_guessed(self):
        self.client.session.get.side_effect = [_response(), _response(WAN_JSON_UNKNOWN)]
        wan = self.client.get_wan_status()
        self.assertIn("WAN_status_error", wan)
        self.assertNotIn("WAN_connected", wan)

    def test_tr181_wan_and_optical(self):
        self.client.session.get.side_effect = [
            _response(),
            _response(WAN_JSON_TR181),
            _response(),
            _response(OPTICAL_XML),
        ]
        wan = self.client.get_wan_status()
        self.assertNotIn("WAN_status_error", wan)
        self.assertTrue(wan["WAN_connected"])
        self.assertEqual(wan["WAN_public_ip"], "203.0.113.7")
        self.assertEqual(wan["WAN_dns_servers"], ["198.51.100.1", "198.51.100.2"])
        self.assertNotIn("WAN_gateway", wan)
        self.assertEqual(wan["PON_rx_power_dbm"], -24.5593)
        self.assertEqual(wan["PON_tx_power_dbm"], 2.629)
        self.assertEqual(wan["PON_temperature_c"], 53.421)
        self.assertFalse(wan["PON_loss_of_signal"])
        self.assertEqual(wan["PON_registration_status"], 5)

    def test_json_session_timeout_relogs_in(self):
        self.client.login = MagicMock(return_value=True)
        self.client.logout = MagicMock()
        self.client.session.get.side_effect = [
            _response(),
            _response(TIMEOUT_JSON),
            _response(),
            _response(WAN_JSON),
        ]
        self.assertTrue(self.client.get_wan_status()["WAN_connected"])
        self.client.login.assert_called_once()
