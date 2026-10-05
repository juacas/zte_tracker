"""H168A V2.1 (#112): clients are listed under OBJ_LOCALNETWORK_STATUS_ACCESSDEV_ID."""

import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

NODE = "OBJ_LOCALNETWORK_STATUS_ACCESSDEV_ID"

RESPONSE = f"""<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <{NODE}>
    <Instance>
      <ParaName>HostName</ParaName><ParaValue>phone</ParaValue>
      <ParaName>IPAddress</ParaName><ParaValue>192.168.1.10</ParaValue>
      <ParaName>Active</ParaName><ParaValue>1</ParaValue>
      <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:01</ParaValue>
      <ParaName>AliasName</ParaName><ParaValue>SSID1</ParaValue>
    </Instance>
    <Instance>
      <ParaName>HostName</ParaName><ParaValue>tv</ParaValue>
      <ParaName>IPAddress</ParaName><ParaValue>192.168.1.11</ParaValue>
      <ParaName>Active</ParaName><ParaValue>0</ParaValue>
      <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:02</ParaValue>
      <ParaName>AliasName</ParaName><ParaValue>LAN1</ParaValue>
    </Instance>
  </{NODE}></ajax_response_xml_root>"""


class TestH168AProfile(TestCase):
    def setUp(self):
        self.cls = _load_client()

    def test_model_is_listed(self):
        self.assertIn("H168A", self.cls.get_models())

    def test_node_names_and_shared_endpoints(self):
        h168a = self.cls("192.168.1.1", "admin", "pw", "H168A").paths
        self.assertEqual(h168a["wlan_id_element"], NODE)
        self.assertEqual(h168a["lan_id_element"], NODE)
        h288a = self.cls("192.168.1.1", "admin", "pw", "H288A").paths
        self.assertEqual(h168a["wlan_script"], h288a["wlan_script"])
        self.assertEqual(h168a["lan_script"], h288a["lan_script"])

    def test_devices_are_parsed_with_the_h168a_profile(self):
        client = self.cls("192.168.1.1", "admin", "pw", "H168A")
        devices = client.parse_devices(
            RESPONSE, client.paths["wlan_id_element"], "WLAN"
        )
        self.assertEqual(
            [d["MACAddress"] for d in devices],
            ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
        )
        self.assertEqual([d["Active"] for d in devices], [True, False])

    def test_other_h288a_family_profiles_are_unchanged(self):
        for model in ("H288A", "H169A", "H388X", "H3640", "H6745"):
            paths = self.cls("192.168.1.1", "admin", "pw", model).paths
            self.assertEqual(paths["wlan_id_element"], "OBJ_ACCESSDEV_ID", model)
            self.assertEqual(paths["lan_id_element"], "OBJ_ACCESSDEV_ID", model)
