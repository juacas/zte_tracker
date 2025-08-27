"""Test configuration for ZTE Tracker integration."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain="zte_tracker",
        title="ZTE Router",
        data={
            "host": "192.168.1.1",
            "username": "admin", 
            "password": "admin",
            "model": "F6640",
        },
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = Mock()
    hass.helpers = Mock()
    return hass


@pytest.fixture
def mock_zte_client():
    """Create a mock ZTE client."""
    client = AsyncMock()
    client.login = AsyncMock(return_value=True)
    client.get_connected_devices = AsyncMock(return_value=[])
    client.logout = AsyncMock()
    return client