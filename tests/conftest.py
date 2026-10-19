"""Test configuration for ZTE Tracker integration."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry


@pytest.fixture(autouse=True)
def enable_event_loop_debug():
    """Override pytest-homeassistant-custom-component's fixture of the same name.

    Python 3.13 removed asyncio.get_event_loop()'s implicit loop creation, so the
    upstream fixture raises RuntimeError for any sync test with no running loop.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.set_debug(True)
    yield
    loop.set_debug(False)


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


@pytest.fixture
def fake_e2633(socket_enabled):
    """A fake ZTE E2633 router on 127.0.0.1 (see tests/_fake_e2633.py).

    pytest-socket blocks every socket in this repo's test run; ``socket_enabled``
    opens them for this test only (the HA test plugin still restricts connections
    to 127.0.0.1). Function scoped, so each test gets a fresh router.
    """
    from _fake_e2633 import FakeE2633

    router = FakeE2633()
    router.start()
    yield router
    router.stop()
