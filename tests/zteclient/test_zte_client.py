import base64
import hashlib
import logging
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives.asymmetric import padding as crypto_padding

from custom_components.zte_tracker.zteclient import zte_client as zte_client_module
from custom_components.zte_tracker.zteclient.zte_client import zteClient


class TestzteClient(TestCase):
    def setUp(self) -> None:
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.setLevel(logging.DEBUG)
        self.password = os.environ.get("TEST_PASSWORD", "!secret")
        self.host = os.environ.get("TEST_HOST", "192.168.3.1")
        # Specify a supported model; defaults for query flags will be used
        self.client = zteClient(self.host, "admin", self.password, "F6640")

    # def test_reboot(self):
    #    self.fail()

    def test_login(self):
        res = self.client.login()
        self.client.logout()
        self.assertTrue(res)
        self.assertEqual(self.client.status, "on")

    # def test_logout(self):
    #    self.fail()

    def test_get_devices_response(self):
        self.client.login()
        devices = self.client.get_devices_response()
        self.client.logout()
        self.assertGreaterEqual(len(devices), 1)

    # --- reboot() Check header tests (no real router required) ---
    
    def _mock_reboot_dependencies(self, client, session_token="TESTTOKEN"):
        """Stub out login/session so reboot() runs without touching a real router."""
        client.login = MagicMock(return_value=True)
        client.get_session_token = MagicMock(return_value=session_token)
        client.logout = MagicMock()

        mock_session = MagicMock()
        client.session = mock_session

        get_response = MagicMock()
        get_response.raise_for_status = MagicMock()
        mock_session.get.return_value = get_response

        post_response = MagicMock()
        post_response.raise_for_status = MagicMock()
        post_response.content = (
            b"<ajax_response_xml_root><IF_ERRORSTR>SUCC</IF_ERRORSTR>"
            b"</ajax_response_xml_root>"
        )
        post_response.text = post_response.content.decode()
        mock_session.post.return_value = post_response

        return mock_session

    def test_reboot_check_header_encrypted(self):
        """Models with reboot_check_encrypted=True (default) must encrypt the
        SHA256 hex digest of the POST body with the model's RSA public key
        under PKCS1v15 padding, then base64-encode the result as Check."""
        client = zteClient(self.host, "admin", self.password, "F6640")
        session_token = "TESTTOKEN"
        mock_session = self._mock_reboot_dependencies(client, session_token=session_token)

        fake_ciphertext = b"FAKE_ENCRYPTED_BYTES"
        mock_public_key = MagicMock()
        mock_public_key.encrypt.return_value = fake_ciphertext

        with patch.object(
            zte_client_module.serialization,
            "load_pem_public_key",
            return_value=mock_public_key,
        ) as mock_load_key:
            result = client.reboot()

        self.assertTrue(result)
        mock_load_key.assert_called_once()

        post_data = f"IF_ACTION=Restart&Btn_restart=&_sessionTOKEN={session_token}"
        expected_digest = hashlib.sha256(post_data.encode("utf-8")).hexdigest()

        mock_public_key.encrypt.assert_called_once()
        call_args, _ = mock_public_key.encrypt.call_args
        encrypted_input, used_padding = call_args[0], call_args[1]
        self.assertEqual(encrypted_input, expected_digest.encode("utf-8"))
        self.assertIsInstance(used_padding, crypto_padding.PKCS1v15)

        _, kwargs = mock_session.post.call_args
        check_header = kwargs["headers"]["Check"]
        self.assertEqual(
            check_header, base64.b64encode(fake_ciphertext).decode("utf-8")
        )

    def test_reboot_check_header_unencrypted(self):
        """H2640 (reboot_check_encrypted=False) must send the raw SHA256 hex
        digest of the POST body as the Check header, unencrypted."""
        client = zteClient(self.host, "admin", self.password, "H2640")
        session_token = "TESTTOKEN"
        mock_session = self._mock_reboot_dependencies(client, session_token=session_token)

        result = client.reboot()

        self.assertTrue(result)
        _, kwargs = mock_session.post.call_args
        check_header = kwargs["headers"]["Check"]

        post_data = f"IF_ACTION=Restart&Btn_restart=&_sessionTOKEN={session_token}"
        expected_digest = hashlib.sha256(post_data.encode("utf-8")).hexdigest()

        self.assertEqual(check_header, expected_digest)

    # --- get_wan_status() DSL parsing test (H2640, from issue #75) ---

    def test_get_wan_status_dsl_h2640(self):
        """H2640 reports its WAN line on dsl_interface_status_lua.lua (OBJ_DSLINTERFACE_ID), not the Ethernet-style ID_WAN_COMFIG node. Uses the real router capture attached to issue #75."""
        client = zteClient(self.host, "admin", self.password, "H2640")
        client.session = MagicMock()

        view_response = MagicMock()
        view_response.raise_for_status = MagicMock()
        client.session.get.return_value = view_response

        data_response = MagicMock()
        data_response.raise_for_status = MagicMock()
        data_response.text = """<ajax_response_xml_root>
    <IF_ERRORPARAM>SUCC</IF_ERRORPARAM>
    <IF_ERRORTYPE>SUCC</IF_ERRORTYPE>
    <IF_ERRORSTR>SUCC</IF_ERRORSTR>
    <IF_ERRORID>0</IF_ERRORID>
    <OBJ_DSLINTERFACE_ID>
        <Instance>
            <ParaName>_InstID</ParaName>
            <ParaValue>IGD.WD1.LINE0</ParaValue>
            <ParaName>Enable</ParaName>
            <ParaValue>1</ParaValue>
            <ParaName>Upstream_noise_margin</ParaName>
            <ParaValue>59</ParaValue>
            <ParaName>Upstream_max_rate</ParaName>
            <ParaValue>16094</ParaValue>
            <ParaName>Downstream_max_rate</ParaName>
            <ParaValue>40879</ParaValue>
            <ParaName>Upstream_current_rate</ParaName>
            <ParaValue>16094</ParaValue>
            <ParaName>Downstream_noise_margin</ParaName>
            <ParaValue>59</ParaValue>
            <ParaName>tLinkEncapsulationUsed</ParaName>
            <ParaValue>G.993.2_Annex_K_PTM</ParaValue>
            <ParaName>Downstream_current_rate</ParaName>
            <ParaValue>40315</ParaValue>
            <ParaName>Downstream_attenuation</ParaName>
            <ParaValue>393</ParaValue>
            <ParaName>CurrentProfile</ParaName>
            <ParaValue>35b</ParaValue>
            <ParaName>Status</ParaName>
            <ParaValue>Up</ParaValue>
            <ParaName>Upstream_attenuation</ParaName>
            <ParaValue>199</ParaValue>
            <ParaName>Module_type</ParaName>
            <ParaValue>VDSL2</ParaValue>
        </Instance>
    </OBJ_DSLINTERFACE_ID>
</ajax_response_xml_root>"""
        client.session.get.side_effect = [view_response, data_response]

        wan_attrs = client.get_wan_status()

        self.assertEqual(wan_attrs["DSL_line_status"], "Up")
        self.assertEqual(wan_attrs["DSL_upstream_rate_kbps"], 16094)
        self.assertEqual(wan_attrs["DSL_downstream_rate_kbps"], 40315)
        self.assertEqual(wan_attrs["DSL_upstream_max_rate_kbps"], 16094)
        self.assertEqual(wan_attrs["DSL_downstream_max_rate_kbps"], 40879)
        self.assertEqual(wan_attrs["DSL_upstream_noise_margin"], 59)
        self.assertEqual(wan_attrs["DSL_downstream_noise_margin"], 59)
        self.assertEqual(wan_attrs["DSL_upstream_attenuation"], 199)
        self.assertEqual(wan_attrs["DSL_downstream_attenuation"], 393)
        self.assertEqual(wan_attrs["DSL_profile"], "35b")
        self.assertEqual(wan_attrs["DSL_encapsulation"], "G.993.2_Annex_K_PTM")
        # DSL sync != Internet reachability, and no Ethernet-style keys leak in.
        self.assertNotIn("WAN_connected", wan_attrs)
        self.assertNotIn("WAN_uptime", wan_attrs)
        self.assertNotIn("WAN_error_message", wan_attrs)

    def test_get_wan_status_default_model_is_unaffected(self):
        """Regression guard for the H2640 DSL branch (#75/#82): any model without wan_status_kind="dsl" must keep hitting ID_WAN_COMFIG and parsing WANCName/ConnStatus/UpTime exactly as before."""
        client = zteClient(self.host, "admin", self.password, "F6640")
        client.session = MagicMock()

        view_response = MagicMock()
        view_response.raise_for_status = MagicMock()
        client.session.get.return_value = view_response

        data_response = MagicMock()
        data_response.raise_for_status = MagicMock()
        data_response.text = """<ajax_response_xml_root>
    <IF_ERRORSTR>SUCC</IF_ERRORSTR>
    <ID_WAN_COMFIG>
        <Instance>
            <ParaName>WANCName</ParaName>
            <ParaValue>WAN_internet</ParaValue>
            <ParaName>ConnStatus</ParaName>
            <ParaValue>Connected</ParaValue>
            <ParaName>UpTime</ParaName>
            <ParaValue>12345</ParaValue>
            <ParaName>RemainLeaseTime</ParaName>
            <ParaValue>600</ParaValue>
        </Instance>
    </ID_WAN_COMFIG>
</ajax_response_xml_root>"""
        client.session.get.side_effect = [view_response, data_response]

        wan_attrs = client.get_wan_status()

        self.assertEqual(wan_attrs["WAN_connected"], True)
        self.assertEqual(wan_attrs["WAN_uptime"], 12345)
        self.assertEqual(wan_attrs["WAN_remain_leasetime"], 600)
        # DSL-only keys must never appear for a non-DSL profile.
        self.assertNotIn("DSL_upstream_rate_kbps", wan_attrs)
        self.assertNotIn("DSL_profile", wan_attrs)
