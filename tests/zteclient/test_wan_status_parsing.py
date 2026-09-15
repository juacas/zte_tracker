"""Unit tests for get_wan_status(), captured live from an F6600P router.

The fixture below is the wan_internetstatus_lua.lua response as returned by
the router once the view request was made first (see the comment in
support_bundle._probe_matrix for why order matters here).
"""

import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

SAMPLE = """<ajax_response_xml_root><IF_ERRORPARAM>SUCC</IF_ERRORPARAM><IF_ERRORTYPE>SUCC</IF_ERRORTYPE><IF_ERRORSTR>SUCC</IF_ERRORSTR><IF_ERRORID>0</IF_ERRORID><ID_WAN_COMFIG><Instance><ParaName>_InstID</ParaName><ParaValue>IGD.WD1.WCD1.WCIP1</ParaValue><ParaName>UpTime</ParaName><ParaValue>873702</ParaValue><ParaName>ConnError</ParaName><ParaValue>ERROR_NONE</ParaValue><ParaName>WANCName</ParaName><ParaValue>WAN_internet</ParaValue><ParaName>RemainLeaseTime</ParaName><ParaValue>11905</ParaValue><ParaName>DNS1</ParaName><ParaValue>10.222.100.30</ParaValue><ParaName>IPAddress</ParaName><ParaValue>94.131.34.223</ParaValue><ParaName>DNS2</ParaName><ParaValue>1.1.1.1</ParaValue><ParaName>GateWay</ParaName><ParaValue>94.131.34.254</ParaValue><ParaName>SubnetMask</ParaName><ParaValue>255.255.255.0</ParaValue><ParaName>DNS3</ParaName><ParaValue>8.8.8.8</ParaValue><ParaName>ConnStatus</ParaName><ParaValue>Connected</ParaValue></Instance></ID_WAN_COMFIG></ajax_response_xml_root>"""


def _make_client(response_text):
    client_cls = _load_client()
    client = object.__new__(client_cls)
    client.query_wan_status = True
    client.paths = {
        "type_first_request": "menuView",
        "tag_wan_status_view": "ethWanStatus&Menu3Location=0",
        "type_main_request": "menuData",
        "tag_wan_status_data": "wan_internetstatus_lua.lua&TypeUplink=2&pageType=1",
    }
    client.base_url = "http://192.168.1.1"
    client.verify_ssl = False
    client.guid = 1
    view_response = MagicMock(text="<ajax_response_xml_root/>", request=None)
    data_response = MagicMock(text=response_text, request=None)
    client.session = MagicMock()
    client.session.get.side_effect = [view_response, data_response]
    return client


class TestWanStatusParsing(TestCase):
    def test_public_ip_and_dns_are_exposed(self):
        client = _make_client(SAMPLE)
        attrs = client.get_wan_status()
        self.assertEqual(attrs["WAN_public_ip"], "94.131.34.223")
        self.assertEqual(
            attrs["WAN_dns_servers"], ["10.222.100.30", "1.1.1.1", "8.8.8.8"]
        )
        self.assertEqual(attrs["WAN_gateway"], "94.131.34.254")
        self.assertEqual(attrs["WAN_subnet_mask"], "255.255.255.0")

    def test_existing_fields_unaffected(self):
        client = _make_client(SAMPLE)
        attrs = client.get_wan_status()
        self.assertEqual(attrs["WAN_uptime"], 873702)
        self.assertEqual(attrs["WAN_remain_leasetime"], 11905)
        self.assertTrue(attrs["WAN_connected"])

    def test_view_request_is_made_before_data_request(self):
        """Asserts the sequencing get_wan_status relies on, and that the test
        fixture's side_effect order matches it: a router that answered the
        data request first would report SessionTimeout here in real life."""
        client = _make_client(SAMPLE)
        client.get_wan_status()
        first_call_tag = client.session.get.call_args_list[0].args[0]
        second_call_tag = client.session.get.call_args_list[1].args[0]
        self.assertIn("ethWanStatus", first_call_tag)
        self.assertIn("wan_internetstatus_lua.lua", second_call_tag)
