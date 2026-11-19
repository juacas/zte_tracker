"""H6745V3 WAN port traffic counters (#128/#133).

eth_sfp_interface_status_lua.lua (under the ethSfpWanStatus view) exposes 64-bit
byte/packet counters for the WAN port. UPnP IGD saturates its 32-bit counters on
this unit, so these web counters are the only usable throughput source. Parsed
only when the profile sets tag_wan_traffic_data (H6745V3), other models are
unaffected.
"""

from unittest import TestCase
from unittest.mock import MagicMock

from test_router_details_parsing import _load_client

WAN_XML = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <ID_WAN_COMFIG>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>PPP Untagged</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>507868</ParaValue>
    </Instance>
  </ID_WAN_COMFIG>
</ajax_response_xml_root>"""

# eth_sfp_interface_status_lua.lua: the WAN port is the Status=Up instance; a
# second NoLink SFP instance must be ignored.
ETH_SFP_XML = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <OBJ_ETH_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>IGD.WD1.ETH1</ParaValue>
      <ParaName>Status</ParaName><ParaValue>Up</ParaValue>
      <ParaName>LinkSpeed</ParaName><ParaValue>2500</ParaValue>
      <ParaName>BytesReceived</ParaName><ParaValue>147233830681</ParaValue>
      <ParaName>BytesSent</ParaName><ParaValue>25363045745</ParaValue>
      <ParaName>PacketsReceived</ParaName><ParaValue>120126906</ParaValue>
      <ParaName>PacketsSent</ParaName><ParaValue>42146335</ParaValue>
    </Instance>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>IGD.WD2.ETH1</ParaValue>
      <ParaName>Status</ParaName><ParaValue>NoLink</ParaValue>
      <ParaName>LinkSpeed</ParaName><ParaValue>Auto</ParaValue>
      <ParaName>BytesReceived</ParaName><ParaValue>0</ParaValue>
      <ParaName>BytesSent</ParaName><ParaValue>0</ParaValue>
    </Instance>
  </OBJ_ETH_ID>
</ajax_response_xml_root>"""


def _response(text=""):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    return r


class TestWanTraffic(TestCase):
    def setUp(self):
        self.cls = _load_client()

    def _client(self, model):
        client = self.cls("192.168.1.1", "admin", "pw", model)
        client.session = MagicMock()
        return client

    def test_profile_sets_the_traffic_tag(self):
        p = self.cls("192.168.1.1", "admin", "pw", "H6745V3").paths
        self.assertEqual(p["tag_wan_traffic_data"], "eth_sfp_interface_status_lua.lua")

    def test_counters_from_the_status_up_port_are_added(self):
        client = self._client("H6745V3")
        # get_wan_status: WAN view + WAN data, then the traffic view + traffic data.
        client.session.get.side_effect = [
            _response(),
            _response(WAN_XML),
            _response(),
            _response(ETH_SFP_XML),
        ]

        attrs = client.get_wan_status()

        traffic_url = client.session.get.call_args_list[3].args[0]
        self.assertIn("_tag=eth_sfp_interface_status_lua.lua", traffic_url)
        self.assertEqual(attrs["WAN_rx_bytes"], 147233830681)
        self.assertEqual(attrs["WAN_tx_bytes"], 25363045745)
        self.assertEqual(attrs["WAN_rx_packets"], 120126906)
        self.assertEqual(attrs["WAN_tx_packets"], 42146335)
        self.assertEqual(attrs["WAN_link_speed_mbps"], 2500)
        # The connection status from the WAN page is still there.
        self.assertEqual(attrs["WAN_connected"], True)

    def test_traffic_failure_does_not_break_wan_status(self):
        client = self._client("H6745V3")
        # The traffic view request raises; WAN status must still be returned.
        client.session.get.side_effect = [
            _response(),
            _response(WAN_XML),
            RuntimeError("boom"),
        ]

        attrs = client.get_wan_status()

        self.assertEqual(attrs["WAN_connected"], True)
        self.assertNotIn("WAN_rx_bytes", attrs)

    def test_other_models_do_not_fetch_the_traffic_page(self):
        client = self._client("F6640")
        client.session.get.side_effect = [_response(), _response(WAN_XML)]

        attrs = client.get_wan_status()

        self.assertEqual(client.session.get.call_count, 2)
        self.assertNotIn("WAN_rx_bytes", attrs)
