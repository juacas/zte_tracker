"""H6745 V3 (V3.0.0P9_IT, Open Fiber), #128.

The H6745 alias of H288A fails on this firmware: the WAN page is
``ethSfpWanStatus`` (``ethWanStatus`` does not exist) and ``wan_internet_lua.lua``
returns several instances, none named ``WAN_internet``. The profile also opts
into ``prefer_connected_wan`` so the Connected instance is picked instead of
``instances[0]`` (a DHCP instance stuck in Connecting), without changing any
other model.
"""

from unittest import TestCase
from unittest.mock import MagicMock

from test_router_details_parsing import _load_client

# wan_internet_lua.lua: no instance is named WAN_internet; the real connection
# is the PPPoE instance whose ConnStatus is Connected, not instances[0].
WAN_NO_INTERNET_NAME = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <ID_WAN_COMFIG>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>DHCP</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connecting</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>0</ParaValue>
    </Instance>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>PPP Untagged</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>507868</ParaValue>
    </Instance>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>PPP Tagged</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connecting</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>0</ParaValue>
    </Instance>
  </ID_WAN_COMFIG>
</ajax_response_xml_root>"""

# A named WAN_internet instance must still win over the Connected heuristic.
WAN_WITH_INTERNET_NAME = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <ID_WAN_COMFIG>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>PPP Untagged</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>111</ParaValue>
    </Instance>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>WAN_internet</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>999</ParaValue>
    </Instance>
  </ID_WAN_COMFIG>
</ajax_response_xml_root>"""

# accessdev_ssiddev_lua.lua (OBJ_ACCESSDEV_ID), one active WLAN client.
WLAN_DEVICES = """<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <OBJ_ACCESSDEV_ID>
    <Instance>
      <ParaName>HostName</ParaName><ParaValue>phone</ParaValue>
      <ParaName>IPAddress</ParaName><ParaValue>192.168.1.10</ParaValue>
      <ParaName>Active</ParaName><ParaValue>1</ParaValue>
      <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:01</ParaValue>
      <ParaName>AliasName</ParaName><ParaValue>SSID1</ParaValue>
    </Instance>
  </OBJ_ACCESSDEV_ID></ajax_response_xml_root>"""

# A real client whose hostname contains the word SessionTimeout must not be
# mistaken for the SessionTimeout error body (IF_ERRORSTR is SUCC here).
WLAN_DEVICES_TIMEOUT_HOSTNAME = """<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <OBJ_ACCESSDEV_ID>
    <Instance>
      <ParaName>HostName</ParaName><ParaValue>SessionTimeout-pc</ParaValue>
      <ParaName>IPAddress</ParaName><ParaValue>192.168.1.20</ParaValue>
      <ParaName>Active</ParaName><ParaValue>1</ParaValue>
      <ParaName>MACAddress</ParaName><ParaValue>aa:bb:cc:dd:ee:09</ParaValue>
      <ParaName>AliasName</ParaName><ParaValue>SSID1</ParaValue>
    </Instance>
  </OBJ_ACCESSDEV_ID></ajax_response_xml_root>"""

TIMEOUT = (
    "<ajax_response_xml_root><IF_ERRORSTR>SessionTimeout</IF_ERRORSTR>"
    "</ajax_response_xml_root>"
)


def _response(text=""):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    return r


class TestH6745V3Profile(TestCase):
    def setUp(self):
        self.cls = _load_client()

    def _client(self, model):
        client = self.cls("192.168.1.1", "admin", "pw", model)
        client.session = MagicMock()
        return client

    # --- profile -------------------------------------------------------
    def test_model_is_listed(self):
        self.assertIn("H6745V3", self.cls.get_models())

    def test_profile_tags_and_inherited_endpoints(self):
        p = self.cls("192.168.1.1", "admin", "pw", "H6745V3").paths
        self.assertEqual(p["tag_wan_status_view"], "ethSfpWanStatus&Menu3Location=0")
        self.assertEqual(
            p["tag_wan_status_data"], "wan_internet_lua.lua&TypeUplink=2&pageType=1"
        )
        self.assertTrue(p["prefer_connected_wan"])
        # LAN/WLAN scripts are inherited from H288A.
        h288a = self.cls("192.168.1.1", "admin", "pw", "H288A").paths
        self.assertEqual(p["wlan_script"], h288a["wlan_script"])
        self.assertEqual(p["lan_script"], h288a["lan_script"])

    def test_other_models_do_not_get_the_flag(self):
        for model in ("H288A", "H6745", "F6640"):
            paths = self.cls("192.168.1.1", "admin", "pw", model).paths
            self.assertNotIn("prefer_connected_wan", paths, model)

    # --- WAN instance selection ---------------------------------------
    def test_wan_prefers_the_connected_instance(self):
        client = self._client("H6745V3")
        client.session.get.side_effect = [_response(), _response(WAN_NO_INTERNET_NAME)]

        attrs = client.get_wan_status()

        view_url = client.session.get.call_args_list[0].args[0]
        self.assertIn("_type=menuView&_tag=ethSfpWanStatus", view_url)
        self.assertEqual(attrs["WAN_connected"], True)
        self.assertEqual(attrs["WAN_uptime"], 507868)

    def test_named_wan_internet_still_wins(self):
        client = self._client("H6745V3")
        client.session.get.side_effect = [_response(), _response(WAN_WITH_INTERNET_NAME)]

        attrs = client.get_wan_status()

        self.assertEqual(attrs["WAN_uptime"], 999)

    def test_other_models_keep_the_instances0_fallback(self):
        """Without the flag, the first instance wins even if a later one is Connected."""
        client = self._client("F6640")
        client.session.get.side_effect = [_response(), _response(WAN_NO_INTERNET_NAME)]

        attrs = client.get_wan_status()

        # instances[0] is the Connecting DHCP instance.
        self.assertEqual(attrs["WAN_connected"], False)
        self.assertEqual(attrs["WAN_uptime"], 0)

    # --- WiFi SessionTimeout fallback ---------------------------------
    def test_wifi_session_timeout_falls_back_then_succeeds(self):
        client = self._client("H6745V3")
        # direct WLAN request -> SessionTimeout body; fallback view ok; WLAN data ok.
        client.session.get.side_effect = [
            _response(TIMEOUT),
            _response(),
            _response(WLAN_DEVICES),
        ]

        devices = client.get_wifi_devices()

        self.assertEqual(client.session.get.call_count, 3)
        self.assertEqual([d["MACAddress"] for d in devices], ["AA:BB:CC:DD:EE:01"])

    def test_wifi_session_timeout_twice_returns_none(self):
        client = self._client("H6745V3")
        client.session.get.side_effect = [
            _response(TIMEOUT),
            _response(),
            _response(TIMEOUT),
        ]

        self.assertIsNone(client.get_wifi_devices())

    def test_hostname_containing_sessiontimeout_is_not_an_error(self):
        """A direct WLAN response with IF_ERRORSTR=SUCC is used as-is, even if a
        hostname contains the word SessionTimeout; no fallback, device returned."""
        client = self._client("H6745V3")
        client.session.get.side_effect = [_response(WLAN_DEVICES_TIMEOUT_HOSTNAME)]

        devices = client.get_wifi_devices()

        self.assertEqual(client.session.get.call_count, 1)
        self.assertEqual([d["MACAddress"] for d in devices], ["AA:BB:CC:DD:EE:09"])
