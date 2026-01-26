import logging
import os
from unittest import TestCase

from zteclient.zte_client import zteClient


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
