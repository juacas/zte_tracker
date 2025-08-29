"""Common fixtures for ZTE Tracker tests."""
import pytest
from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME


class MockHomeAssistant:
    """Mock HomeAssistant for testing."""
    
    def __init__(self):
        self.data = {}
        self.config_entries = Mock()
        self.states = Mock()
        self.services = Mock()
        
    async def async_add_executor_job(self, func, *args):
        """Mock executor job."""
        return func(*args) if callable(func) else func


@pytest.fixture
def hass():
    """Mock HomeAssistant."""
    return MockHomeAssistant()


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.domain = "zte_tracker"
    entry.title = "Test Router"
    entry.data = {
        CONF_HOST: "192.168.1.1",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "password",
        CONF_MODEL: "F6640",
    }
    entry.options = {}
    entry.source = "user"
    entry.version = 1
    return entry


@pytest.fixture
def mock_zte_client():
    """Create a mock ZTE client."""
    client = Mock()
    client.host = "192.168.1.1"
    client.model = "F6640"
    client.login.return_value = True
    client.logout.return_value = None
    client.get_devices_response.return_value = [
        {
            "HostName": "TestDevice",
            "IPAddress": "192.168.1.100",
            "MACAddress": "00:11:22:33:44:55",
            "Active": True,
            "IconType": "smartphone",
            "NetworkType": "WLAN",
        }
    ]
    return client