"""Unit tests for F680 parental-control parsing and writes."""

import base64
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
        "type_first_request": "menuView",
        "type_main_request": "menuData",
        "tag_parentctrl_view": "parentCtrl&Menu3Location=0",
        "tag_parentctrl_data": "firewall_parentctrl_lua.lua",
    }
    client.model = "F680"
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

    def test_set_parental_control_enabled_posts_signed_form(self):
        client = _make_client()
        view = MagicMock(
            text="var _sessionTmpToken = \"ab\\x2dcd\";", request=None
        )
        view.raise_for_status = Mock()
        response = MagicMock(text=SUCCESS, request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = view
        client.session.post.return_value = response

        self.assertTrue(
            client.set_parental_control_enabled("DEV.PCUser1", enabled=True)
        )

        view_url = client.session.get.call_args.args[0]
        self.assertIn("?_type=menuView", view_url)
        self.assertIn("_tag=parentCtrl&Menu3Location=0", view_url)
        kwargs = client.session.post.call_args.kwargs
        self.assertEqual(
            kwargs["data"],
            "IF_ACTION=Apply&Enable=1&_InstID=DEV.PCUser1&_sessionTOKEN=ab-cd",
        )
        # RSA PKCS#1 v1.5 is randomised, so check only the 2048-bit ciphertext size.
        self.assertEqual(len(base64.b64decode(kwargs["headers"]["Check"])), 256)
        self.assertIn(
            "application/x-www-form-urlencoded", kwargs["headers"]["Content-Type"]
        )
        request_url = client.session.post.call_args.args[0]
        self.assertIn("?_type=menuData", request_url)
        self.assertIn("_tag=firewall_parentctrl_lua.lua", request_url)

    def test_set_parental_control_enabled_rejects_unrecognised_response(self):
        client = _make_client()
        view = MagicMock(text="var _sessionTmpToken = \"t\";", request=None)
        view.raise_for_status = Mock()
        response = MagicMock(text="<html></html>", request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = view
        client.session.post.return_value = response

        self.assertFalse(
            client.set_parental_control_enabled("DEV.PCUser1", enabled=True)
        )

    def test_get_parental_controls_returns_none_on_failure(self):
        client = _make_client()
        client.session.get.side_effect = RuntimeError("boom")

        self.assertIsNone(client.get_parental_controls())

    def test_get_parental_controls_rejects_non_data_responses(self):
        bodies = (
            "<html></html>",
            "<ajax_response_xml_root><IF_ERRORID>-1</IF_ERRORID>"
            "</ajax_response_xml_root>",
        )
        for body in bodies:
            client = _make_client()
            response = MagicMock(text=body, request=None)
            response.raise_for_status = Mock()
            client.session.get.return_value = response
            self.assertIsNone(client.get_parental_controls(), body)

    def test_get_parental_controls_without_session_is_a_failure(self):
        client = _make_client()
        client.session = None

        self.assertIsNone(client.get_parental_controls())

    def test_get_parental_controls_empty_rule_list_is_valid(self):
        client = _make_client()
        body = (
            "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
            "<IF_ERRORID>0</IF_ERRORID></ajax_response_xml_root>"
        )
        response = MagicMock(text=body, request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = response

        self.assertEqual(client.get_parental_controls(), [])

    def test_check_header_key_size_follows_model(self):
        for model, size in (("F680", 256), ("F6600P", 512), ("F6745Q", 256)):
            client = _make_client()
            client.model = model
            check = client._check_header("a=b")
            self.assertEqual(len(base64.b64decode(check)), size)

    def test_check_header_unencrypted_is_plain_sha256(self):
        import hashlib

        client = _make_client()
        self.assertEqual(
            client._check_header("a=b", False),
            hashlib.sha256(b"a=b").hexdigest(),
        )

    def test_check_header_is_not_logged(self):
        client = _make_client()
        self.assertIn("check", client._SENSITIVE_HEADERS)

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

    def test_get_parental_controls_logs_why_it_was_skipped(self):
        client = _make_client()
        client.model = "F6640"
        client.paths = {"type_main_request": "menuData"}

        with self.assertLogs(level="DEBUG") as logs:
            self.assertEqual(client.get_parental_controls(), [])

        output = "\n".join(logs.output)
        self.assertIn("model=F6640", output)
        self.assertIn("has_parentctrl_tag=False", output)
        client.session.get.assert_not_called()

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

    def _get_with_body(self, body):
        client = _make_client()
        response = MagicMock(text=body, request=None)
        response.raise_for_status = Mock()
        client.session.get.return_value = response
        return client

    def test_get_parental_controls_rejects_router_error_with_instances(self):
        error_str = SAMPLE.replace(
            "<IF_ERRORSTR>SUCC</IF_ERRORSTR>", "<IF_ERRORSTR>FAIL</IF_ERRORSTR>"
        )
        error_id = SAMPLE.replace(
            "<IF_ERRORID>0</IF_ERRORID>", "<IF_ERRORID>-1</IF_ERRORID>"
        )
        for body in (error_str, error_id):
            self.assertIsNone(self._get_with_body(body).get_parental_controls())

    def test_get_parental_controls_instances_without_fields_is_a_failure(self):
        body = (
            "<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
            "<IF_ERRORID>0</IF_ERRORID><Instance><ParaName>Name</ParaName>"
            "<ParaValue>x</ParaValue></Instance></ajax_response_xml_root>"
        )
        self.assertIsNone(self._get_with_body(body).get_parental_controls())

    def test_get_parental_controls_parses_textual_enable_values(self):
        body = SAMPLE.replace(
            "<ParaName>Enable</ParaName><ParaValue>1</ParaValue>",
            "<ParaName>Enable</ParaName><ParaValue>true</ParaValue>",
        )
        rules = self._get_with_body(body).get_parental_controls()

        self.assertEqual([rule["enabled"] for rule in rules], [False, True])

    def test_get_parental_controls_warns_once_per_outage(self):
        client = _make_client()
        client.session.get.side_effect = RuntimeError("boom")

        with self.assertLogs(level="DEBUG") as logs:
            client.get_parental_controls()
            client.get_parental_controls()

        levels = [record.levelname for record in logs.records]
        self.assertEqual(levels.count("WARNING"), 1)
        self.assertEqual(levels.count("DEBUG"), 1)

        response = MagicMock(text=SAMPLE, request=None)
        response.raise_for_status = Mock()
        client.session.get.side_effect = None
        client.session.get.return_value = response
        self.assertTrue(client.get_parental_controls())

        client.session.get.side_effect = RuntimeError("boom")
        with self.assertLogs(level="WARNING"):
            client.get_parental_controls()

    def test_set_parental_control_enabled_rejects_router_errors(self):
        for body in (
            SUCCESS.replace("<IF_ERRORSTR>SUCC<", "<IF_ERRORSTR>FAIL<"),
            SUCCESS.replace("<IF_ERRORID>0<", "<IF_ERRORID>-1<"),
        ):
            client = _make_client()
            view = MagicMock(text='var _sessionTmpToken = "t";', request=None)
            view.raise_for_status = Mock()
            response = MagicMock(text=body, request=None)
            response.raise_for_status = Mock()
            client.session.get.return_value = view
            client.session.post.return_value = response

            self.assertFalse(
                client.set_parental_control_enabled("DEV.PCUser1", enabled=True)
            )
