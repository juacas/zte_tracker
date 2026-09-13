import hashlib
import logging
import os
from unittest import TestCase
from unittest.mock import MagicMock

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

        # menuView GET (rebootAndReset) just needs to not raise
        get_response = MagicMock()
        get_response.raise_for_status = MagicMock()
        mock_session.get.return_value = get_response

        # POST response: successful XML body
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
        """Models with reboot_check_encrypted=True (default) must send an
        RSA-encrypted Check header, not the raw SHA256 hex digest."""
        client = zteClient(self.host, "admin", self.password, "F6640")
        mock_session = self._mock_reboot_dependencies(client, session_token="TESTTOKEN")

        result = client.reboot()

        self.assertTrue(result)
        _, kwargs = mock_session.post.call_args
        check_header = kwargs["headers"]["Check"]

        # A raw SHA256 hex digest is 64 hex chars; the encrypted header is
        # base64-encoded RSA ciphertext and must not look like that.
        self.assertNotEqual(len(check_header), 64)
        with self.assertRaises(ValueError):
            int(check_header, 16)

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
