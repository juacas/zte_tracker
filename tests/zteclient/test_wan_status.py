"""get_wan_status() tests: the H2640 DSL branch (#75) and the Ethernet default."""

from unittest import TestCase
from unittest.mock import MagicMock

from test_router_details_parsing import _load_client

# The real H2640 response attached to issue #75, trimmed to the mapped fields.
DSL_XML = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <OBJ_DSLINTERFACE_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>IGD.WD1.LINE0</ParaValue>
      <ParaName>Upstream_noise_margin</ParaName><ParaValue>60</ParaValue>
      <ParaName>Upstream_max_rate</ParaName><ParaValue>16938</ParaValue>
      <ParaName>Downstream_max_rate</ParaName><ParaValue>41738</ParaValue>
      <ParaName>Upstream_current_rate</ParaName><ParaValue>16937</ParaValue>
      <ParaName>Downstream_noise_margin</ParaName><ParaValue>58</ParaValue>
      <ParaName>tLinkEncapsulationUsed</ParaName><ParaValue>G.993.2_Annex_K_PTM</ParaValue>
      <ParaName>Downstream_current_rate</ParaName><ParaValue>41169</ParaValue>
      <ParaName>Downstream_attenuation</ParaName><ParaValue>388</ParaValue>
      <ParaName>CurrentProfile</ParaName><ParaValue>35b</ParaValue>
      <ParaName>Status</ParaName><ParaValue>Up</ParaValue>
      <ParaName>Upstream_attenuation</ParaName><ParaValue>200</ParaValue>
      <ParaName>Module_type</ParaName><ParaValue>VDSL2</ParaValue>
    </Instance>
  </OBJ_DSLINTERFACE_ID>
</ajax_response_xml_root>"""

ETH_XML = """<ajax_response_xml_root>
  <IF_ERRORSTR>SUCC</IF_ERRORSTR>
  <ID_WAN_COMFIG>
    <Instance>
      <ParaName>WANCName</ParaName><ParaValue>WAN_internet</ParaValue>
      <ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue>
      <ParaName>UpTime</ParaName><ParaValue>12345</ParaValue>
      <ParaName>RemainLeaseTime</ParaName><ParaValue>600</ParaValue>
    </Instance>
  </ID_WAN_COMFIG>
</ajax_response_xml_root>"""

TIMEOUT_XML = (
    "<ajax_response_xml_root><IF_ERRORSTR>SessionTimeout</IF_ERRORSTR>"
    "</ajax_response_xml_root>"
)


def _response(text=""):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.text = text
    return r


class TestGetWanStatus(TestCase):
    def setUp(self):
        self.client_cls = _load_client()

    def _client(self, model):
        client = self.client_cls("192.168.1.1", "admin", "pw", model)
        client.session = MagicMock()
        return client

    def test_h2640_reads_its_own_dsl_page(self):
        """#75: H2640 inherited the Ethernet view tag, so the router answered SessionTimeout. It needs its own dslWanStatus view plus the DSL data tag."""
        client = self._client("H2640")
        client.session.get.side_effect = [_response(), _response(DSL_XML)]

        attrs = client.get_wan_status()

        self.assertEqual(client.session.get.call_count, 2)
        view_url = client.session.get.call_args_list[0].args[0]
        data_url = client.session.get.call_args_list[1].args[0]
        self.assertIn("_type=menuView&_tag=dslWanStatus", view_url)
        self.assertIn("_type=menuData&_tag=dsl_interface_status_lua.lua", data_url)
        self.assertEqual(attrs["DSL_line_status"], "Up")
        self.assertEqual(attrs["DSL_upstream_rate_kbps"], 16937)
        self.assertEqual(attrs["DSL_downstream_rate_kbps"], 41169)
        self.assertEqual(attrs["DSL_upstream_max_rate_kbps"], 16938)
        self.assertEqual(attrs["DSL_downstream_max_rate_kbps"], 41738)
        self.assertEqual(attrs["DSL_upstream_noise_margin"], 60)
        self.assertEqual(attrs["DSL_downstream_noise_margin"], 58)
        self.assertEqual(attrs["DSL_upstream_attenuation"], 200)
        self.assertEqual(attrs["DSL_downstream_attenuation"], 388)
        self.assertEqual(attrs["DSL_profile"], "35b")
        self.assertEqual(attrs["DSL_encapsulation"], "G.993.2_Annex_K_PTM")
        # DSL sync is not Internet reachability, so no WAN_connected is claimed.
        self.assertNotIn("WAN_connected", attrs)

    def test_ethernet_models_are_unchanged(self):
        client = self._client("F6640")
        client.session.get.side_effect = [_response(), _response(ETH_XML)]

        attrs = client.get_wan_status()

        self.assertEqual(attrs["WAN_connected"], True)
        self.assertEqual(attrs["WAN_uptime"], 12345)
        self.assertEqual(attrs["WAN_remain_leasetime"], 600)
        self.assertNotIn("DSL_profile", attrs)

    def test_session_timeout_relogs_in_and_retries_once(self):
        client = self._client("F6640")
        client.login = MagicMock(return_value=True)
        client.logout = MagicMock()
        client.session.get.side_effect = [
            _response(),
            _response(TIMEOUT_XML),
            _response(),
            _response(ETH_XML),
        ]

        attrs = client.get_wan_status()

        client.login.assert_called_once()
        self.assertEqual(attrs["WAN_connected"], True)
        self.assertNotIn("WAN_status_error", attrs)

    def test_failure_is_reported_on_the_entity(self):
        """The #75 symptom was an empty attribute set with no clue why."""
        client = self._client("F6640")
        client.login = MagicMock(return_value=True)
        client.logout = MagicMock()
        client.session.get.side_effect = [
            _response(),
            _response(TIMEOUT_XML),
            _response(),
            _response(TIMEOUT_XML),
        ]

        attrs = client.get_wan_status()

        self.assertIn("SessionTimeout", attrs["WAN_status_error"])
