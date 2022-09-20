import os
from unittest import TestCase
from device_tracker import zteDeviceScanner
from .zteclient.zte_client import zteClient


class TestzteDeviceScanner(TestCase):

    def test_scan_devices(self):
        password = os.environ.get('TEST_PASSWORD', 'admin')
        host = os.environ.get('TEST_HOST', '192.168.3.1')
        hass = HassMockup()
        cli = zteClient(host, 'admin', password)
        scanner = zteDeviceScanner(hass, cli)
        devices = scanner.scan_devices()
        print("devices {0}".format(devices))

class HassStatesMockup:
    def __init__(self):
        self.states = 0
    def set(self, data):
        # do nothing
        self.states = 0

class HassMockup:
    def __init__(self):
        self.data = dict()
        self.states = HassStatesMockup()