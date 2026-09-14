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
