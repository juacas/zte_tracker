"""Unit tests for get_pon_optical_info(), captured live from an F6600P router.

Model-gated (see F6600P in zte_client.py): only exercised when
tag_pon_optical_view/tag_pon_optical_data are present in client.paths.
"""

import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

SAMPLE = (
    "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
    "<OBJ_LOS_INFO_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>LosInfo</ParaName><ParaValue>0</ParaValue></Instance></OBJ_LOS_INFO_ID>"
    "<OBJ_GPONREGSTATUS_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>RegStatus</ParaName><ParaValue>5</ParaValue></Instance></OBJ_GPONREGSTATUS_ID>"
    "<OBJ_PON_OPTICALPARA_ID><Instance><ParaName>_InstID</ParaName><ParaValue>IGD</ParaValue>"
    "<ParaName>Current</ParaName><ParaValue>18</ParaValue>"
    "<ParaName>RFTxPower</ParaName><ParaValue>0</ParaValue>"
    "<ParaName>Volt</ParaName><ParaValue>3300</ParaValue>"
    "<ParaName>Temp</ParaName><ParaValue>45.62</ParaValue>"
    "<ParaName>RxPower</ParaName><ParaValue>-18.34</ParaValue>"
    "<ParaName>VideoRxPower</ParaName><ParaValue>0</ParaValue>"
    "<ParaName>TxPower</ParaName><ParaValue>2.15</ParaValue>"
    "</Instance></OBJ_PON_OPTICALPARA_ID></ajax_response_xml_root>"
)


def _make_client(response_text):
    client_cls = _load_client()
    client = object.__new__(client_cls)
    client.paths = {
        "type_first_request": "menuView",
        "tag_pon_optical_view": "ponopticalinfo&Menu3Location=0",
        "type_main_request": "menuData",
        "tag_pon_optical_data": "optical_info_lua.lua",
    }
    client.base_url = "http://192.168.1.1"
    client.verify_ssl = False
    client.guid = 1
    view_response = MagicMock(text="<ajax_response_xml_root/>", request=None)
    data_response = MagicMock(text=response_text, request=None)
    client.session = MagicMock()
    client.session.get.side_effect = [view_response, data_response]
    return client


class TestPonOpticalParsing(TestCase):
    def test_optical_power_and_alarms_are_exposed(self):
        client = _make_client(SAMPLE)
        attrs = client.get_pon_optical_info()
        self.assertEqual(attrs["PON_rx_power_dbm"], -18.34)
        self.assertEqual(attrs["PON_tx_power_dbm"], 2.15)
        self.assertEqual(attrs["PON_temperature_c"], 45.62)
        self.assertFalse(attrs["PON_loss_of_signal"])
        self.assertEqual(attrs["PON_registration_status"], 5)

    def test_view_request_is_made_before_data_request(self):
        client = _make_client(SAMPLE)
        client.get_pon_optical_info()
        first_call_tag = client.session.get.call_args_list[0].args[0]
        second_call_tag = client.session.get.call_args_list[1].args[0]
        self.assertIn("ponopticalinfo", first_call_tag)
        self.assertIn("optical_info_lua.lua", second_call_tag)

    def test_returns_empty_when_model_does_not_define_the_tags(self):
        client = _make_client(SAMPLE)
        client.paths = {"type_first_request": "menuView", "type_main_request": "menuData"}
        self.assertEqual(client.get_pon_optical_info(), {})
        client.session.get.assert_not_called()
