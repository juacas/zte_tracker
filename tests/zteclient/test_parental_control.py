"""Unit tests for F680 parental-control parsing and writes."""

import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_router_details_parsing import _load_client  # noqa: E402

SAMPLE = (
    "<ajax_response_xml_root><IF_ERRORPARAM>SUCC</IF_ERRORPARAM>"
    "<IF_ERRORTYPE>SUCC</IF_ERRORTYPE><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
    "<IF_ERRORID>0</IF_ERRORID>"
    "<Instance><ParaName>_InstID</ParaName><ParaValue>DEV.PCUser1</ParaValue>"
    "<ParaName>Enable</ParaName><ParaValue>0</ParaValue>"
    "<ParaName>ChildId</ParaName><ParaValue>AA:BB:CC:DD:EE:FF</ParaValue>"
    "<ParaName>Name</ParaName><ParaValue>Tv zal</ParaValue></Instance>"
    "<Instance><ParaName>_InstID</ParaName><ParaValue>DEV.PCUser2</ParaValue>"
    "<ParaName>Enable</ParaName><ParaValue>1</ParaValue>"
    "<ParaName>ChildId</ParaName><ParaValue>11:22:33:44:55:66</ParaValue>"
    "<ParaName>Name</ParaName><ParaValue>Tv kitchen</ParaValue></Instance>"
    "</ajax_response_xml_root>"
)

SUCCESS = (
    "<ajax_response_xml_root><INSTIDENTITY>DEV.PCUser1</INSTIDENTITY>"
    "<IF_ERRORID>0</IF_ERRORID><IF_ERRORTYPE>SUCC</IF_ERRORTYPE>"
    "<IF_ERRORSTR>SUCC</IF_ERRORSTR><IF_ERRORPARAM>SUCC</IF_ERRORPARAM>"
    "<_InstID>DEV.PCUser1</_InstID></ajax_response_xml_root>"
)


def _make_client():
    client_cls = _load_client()
    client = object.__new__(client_cls)
    client.paths = {
        "type_main_request": "menuData",
        "tag_parentctrl_data": "firewall_parentctrl_lua.lua",
    }
    client.base_url = "http://192.168.1.1"
    client.verify_ssl = False
    client.guid = 1
    client.session = MagicMock()
    return client


class TestParentalControl(TestCase):
    def test_get_parental_controls_parses_direct_instances(self):
        client = _make_client()
        response = MagicMock(text=SAMPLE, request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = response

        rules = client.get_parental_controls()

        self.assertEqual(
            rules,
            [
                {"id": "DEV.PCUser1", "name": "Tv zal", "enabled": False},
                {"id": "DEV.PCUser2", "name": "Tv kitchen", "enabled": True},
            ],
        )
        request_url = client.session.get.call_args.args[0]
        self.assertIn("?_type=menuData", request_url)
        self.assertIn("_tag=firewall_parentctrl_lua.lua", request_url)

    def test_set_parental_control_enabled_posts_expected_form_fields(self):
        client = _make_client()
        response = MagicMock(text=SUCCESS, request=None)
        response.raise_for_status = Mock()
        client.session.post.return_value = response
        client.get_session_token = Mock(return_value="session-token")

        self.assertTrue(
            client.set_parental_control_enabled("DEV.PCUser1", enabled=True)
        )

        kwargs = client.session.post.call_args.kwargs
        self.assertEqual(
            kwargs["data"],
            {
                "IF_ACTION": "Apply",
                "Enable": "1",
                "_InstID": "DEV.PCUser1",
                "_sessionTOKEN": "session-token",
            },
        )
        self.assertEqual(
            kwargs["headers"]["Content-Type"], "application/x-www-form-urlencoded"
        )
        request_url = client.session.post.call_args.args[0]
        self.assertIn("?_type=menuData", request_url)
        self.assertIn("_tag=firewall_parentctrl_lua.lua", request_url)

    def test_get_parental_controls_logs_counts_without_rule_names(self):
        client = _make_client()
        response = MagicMock(text=SAMPLE, request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = response

        with self.assertLogs(level="DEBUG") as logs:
            client.get_parental_controls()

        output = "\n".join(logs.output)
        self.assertIn("2 rule(s) parsed from 2 instance(s)", output)
        self.assertNotIn("Tv zal", output)
        self.assertNotIn("AA:BB:CC:DD:EE:FF", output)

    def test_get_parental_controls_logs_empty_response(self):
        client = _make_client()
        response = MagicMock(
            text="<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
            "</ajax_response_xml_root>",
            request=None,
        )
        response.raise_for_status = Mock()
        client.session.get.return_value = response

        with self.assertLogs(level="DEBUG") as logs:
            self.assertEqual(client.get_parental_controls(), [])

        self.assertIn("0 rule(s) parsed from 0 instance(s)", "\n".join(logs.output))
