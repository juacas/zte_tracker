import os
from unittest import TestCase
from unittest.mock import Mock, patch
from ..legacy_device_tracker import zteDeviceScanner
from ..zteclient.zte_client import zteClient


class TestzteDeviceScanner(TestCase):

    @patch.object(zteClient, 'login')
    @patch.object(zteClient, 'logout')
    @patch.object(zteClient, 'get_devices_response')
    def test_scan_devices(self, mock_get_devices, mock_logout, mock_login):
        """Test device scanning with mocked responses."""
        # Setup mocks
        mock_login.return_value = True
        mock_get_devices.return_value = [
            {
                'HostName': 'TestDevice',
                'IPAddress': '192.168.1.100',
                'MACAddress': '00:11:22:33:44:55',
                'Active': True,
                'IconType': 'smartphone'
            }
        ]
        
        hass = HassMockup()
        cli = zteClient('192.168.1.1', 'admin', 'password', 'F6640')
        scanner = zteDeviceScanner(hass, cli)
        
        # Test scan
        devices = scanner.scan_devices()
        
        # Verify results
        self.assertTrue(len(devices) > 0)
        self.assertIn('00:11:22:33:44:55', devices)
        mock_login.assert_called_once()
        mock_logout.assert_called_once()

class HassStatesMockup:
    """Mock for Home Assistant states."""
    def __init__(self):
        self.states = {}
    
    def set(self, entity_id, state):
        """Mock setting a state."""
        self.states[entity_id] = state


class HassMockup:
    """Mock for Home Assistant instance."""
    def __init__(self):
        self.data = {}
        self.states = HassStatesMockup()