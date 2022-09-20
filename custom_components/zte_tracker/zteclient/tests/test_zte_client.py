import os
from unittest import TestCase

from zteclient.zte_client import zteClient


class TestzteClient(TestCase):
    def setUp(self) -> None:
        self.password = os.environ.get('TEST_PASSWORD', '!secret')
        self.host = os.environ.get('TEST_HOST', '192.168.3.1')
        self.client = zteClient(self.host, 'admin', self.password)

    # def test_reboot(self):
    #    self.fail()

    def test_login(self):
        res = self.client.login()
        self.client.logout()
        self.assertTrue(res)
        self.assertEquals(self.client.status, 'on')

    # def test_logout(self):
    #    self.fail()

    def test_get_devices_response(self):
        self.client.login()
        devices = self.client.get_devices_response()
        self.client.logout()
        self.assertGreaterEqual(len(devices), 1)
