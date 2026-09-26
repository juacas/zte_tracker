"""Tests for coordinator runtime behavior and legacy scanner fallbacks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker.const import (
    CONF_MESH_TOPOLOGY,
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    CONF_SESSION_REUSE,
    DOMAIN,
)
from custom_components.zte_tracker.coordinator import (
    SESSION_MAX_AGE,
    ZteDataCoordinator,
)
from custom_components.zte_tracker.legacy_device_tracker import (
    get_scanner,
    zteDeviceScanner,
)


def _entry(**overrides) -> MockConfigEntry:
    data = {
        CONF_HOST: "192.168.1.1",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "secret",
        CONF_MODEL: "F6640",
        **overrides.pop("data", {}),
    }
    options = {
        CONF_QUERY_WAN_STATUS: True,
        CONF_QUERY_ROUTER_DETAILS: True,
        CONF_SESSION_REUSE: False,
        CONF_MESH_TOPOLOGY: False,
        **overrides.pop("options", {}),
    }
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry-1",
        data=data,
        options=options,
        **overrides,
    )


def _hass(mock_hass):
    mock_hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    tasks = []

    def _schedule(coro, _name):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    mock_hass.async_create_background_task = Mock(side_effect=_schedule)
    mock_hass._scheduled_tasks = tasks
    return mock_hass


def _client(**kwargs):
    client = SimpleNamespace(
        host="192.168.1.1",
        model="F6640",
        username="admin",
        statusmsg="OK",
        login=Mock(return_value=True),
        logout=Mock(return_value=None),
        reboot=Mock(return_value=True),
        get_devices_response=Mock(return_value=[]),
        get_wan_status=Mock(return_value={}),
        get_router_details=Mock(return_value={}),
        _try_topology=Mock(return_value=None),
        login_data=None,
        session=None,
        query_wan_status=True,
        query_router_details=True,
        mesh_topology=False,
    )
    for key, value in kwargs.items():
        setattr(client, key, value)
    return client


def _make_coordinator(mock_hass, entry, client):
    hass = _hass(mock_hass)
    with patch(
        "custom_components.zte_tracker.coordinator.zteClient", return_value=client
    ):
        coordinator = ZteDataCoordinator(hass, entry)
    return coordinator


@pytest.mark.asyncio
async def test_pause_and_resume_scanning_manage_session_state(mock_hass) -> None:
    """Pausing should log out in the background and resume should reset login state."""
    client = _client()
    coordinator = _make_coordinator(mock_hass, _entry(), client)
    coordinator._last_login_at = datetime.now()
    client.login_data = {"ok": 1}

    coordinator.pause_scanning()
    assert coordinator.paused is True
    await asyncio.gather(*mock_hass._scheduled_tasks)
    client.logout.assert_called_once()
    assert coordinator._last_login_at is None

    coordinator.resume_scanning()
    assert coordinator.paused is False
    assert coordinator.client.login_data is None


@pytest.mark.asyncio
async def test_async_reboot_router_clears_session_age_on_success_and_failure(
    mock_hass,
) -> None:
    """Reboot requests should always invalidate cached session state."""
    client = _client(reboot=Mock(return_value=True))
    coordinator = _make_coordinator(mock_hass, _entry(), client)
    coordinator._last_login_at = datetime.now()

    assert await coordinator.async_reboot_router() is True
    assert coordinator._last_login_at is None

    coordinator._last_login_at = datetime.now()
    client.reboot.side_effect = RuntimeError("boom")
    assert await coordinator.async_reboot_router() is False
    assert coordinator._last_login_at is None


def test_enrich_topology_prefers_legacy_when_mesh_is_smaller(mock_hass) -> None:
    """Partial mesh data should not replace the fuller legacy scan."""
    coordinator = _make_coordinator(mock_hass, _entry(), _client())
    legacy_devices = [{"MACAddress": "AA", "Port": "SSID1"}]
    topo_devices = []

    assert coordinator._enrich_topology(topo_devices, legacy_devices) == legacy_devices


def test_enrich_topology_merges_ports_and_ssids(mock_hass) -> None:
    """Mesh results should inherit missing legacy metadata by MAC and access type."""
    coordinator = _make_coordinator(mock_hass, _entry(), _client())
    legacy_devices = [
        {
            "MACAddress": "AA",
            "Port": "SSID1",
            "ConnectTime": "2026-01-01T10:00:00",
            "LinkTime": "44",
        }
    ]
    topo_devices = [
        {"MACAddress": "AA", "_AccessType": "1", "Port": ""},
        {"MACAddress": "BB", "_AccessType": "1", "Port": ""},
    ]

    merged = coordinator._enrich_topology(topo_devices, legacy_devices)

    assert merged[0]["Port"] == "SSID1"
    assert merged[0]["ConnectTime"] == "2026-01-01T10:00:00"
    assert merged[0]["LinkTime"] == "44"
    assert merged[1]["Port"] == "SSID1"


@pytest.mark.asyncio
async def test_async_update_data_returns_cached_paused_state(mock_hass) -> None:
    """Paused scans should expose cached devices without touching the router."""
    client = _client()
    coordinator = _make_coordinator(mock_hass, _entry(), client)
    coordinator._paused = True
    coordinator._device_cache = {"AA": {"name": "Phone", "active": False}}

    result = await coordinator._async_update_data()

    assert result == {
        "devices": {"AA": {"name": "Phone", "active": False}},
        "router_info": {
            "host": "192.168.1.1",
            "model": "F6640",
            "status": "paused",
        },
    }
    client.login.assert_not_called()


@pytest.mark.asyncio
async def test_async_update_data_legacy_path_uses_cache_on_failure(mock_hass) -> None:
    """Recent cached devices should survive a login failure."""
    client = _client(login=Mock(return_value=False))
    coordinator = _make_coordinator(mock_hass, _entry(), client)
    coordinator._device_cache = {"AA": {"name": "Phone", "active": False}}
    coordinator._last_successful_update = datetime.now()

    result = await coordinator._async_update_data()

    assert coordinator.available is False
    assert result["devices"] == {"AA": {"name": "Phone", "active": False}}
    assert result["router_info"]["status"] == "unavailable"
    client.logout.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_data_legacy_path_enriches_topology(mock_hass) -> None:
    """The legacy fetch path should merge router, WAN, and mesh data."""
    client = _client(
        get_devices_response=Mock(
            return_value=[
                {
                    "HostName": "Phone",
                    "IPAddress": "10.0.0.2",
                    "MACAddress": "AA:BB",
                    "Active": True,
                    "NetworkType": "WLAN",
                    "Port": "SSID1",
                }
            ]
        ),
        get_wan_status=Mock(return_value={"WAN_connected": True}),
        get_router_details=Mock(return_value={"ModelName": "F6600P"}),
        _try_topology=Mock(
            return_value=[
                {
                    "HostName": "Phone",
                    "IPAddress": "10.0.0.2",
                    "MACAddress": "AA:BB",
                    "Active": True,
                    "NetworkType": "WLAN",
                    "Port": "",
                    "_AccessType": "1",
                }
            ]
        ),
    )
    coordinator = _make_coordinator(
        mock_hass, _entry(options={CONF_MESH_TOPOLOGY: True}), client
    )

    result = await coordinator._async_update_data()

    assert coordinator.available is True
    assert result["devices"]["AA:BB"]["port"] == "SSID1"
    assert result["router_info"]["status"] == "connected"
    assert result["router_info"]["WAN_connected"] is True
    assert result["router_info"]["ModelName"] == "F6600P"
    assert client.logout.called


@pytest.mark.asyncio
async def test_async_update_data_reuse_path_reauthenticates_stale_session(
    mock_hass,
) -> None:
    """Old cached sessions should be refreshed before polling."""
    client = _client(
        login=Mock(return_value=True),
        get_devices_response=Mock(
            return_value=[
                {
                    "HostName": "Phone",
                    "IPAddress": "10.0.0.2",
                    "MACAddress": "AA:BB",
                    "Active": True,
                    "NetworkType": "WLAN",
                }
            ]
        ),
    )
    client.login_data = {"ok": 1}
    client.session = object()
    coordinator = _make_coordinator(
        mock_hass, _entry(options={CONF_SESSION_REUSE: True}), client
    )
    coordinator._last_login_at = datetime.now() - SESSION_MAX_AGE - timedelta(seconds=1)

    result = await coordinator._async_update_data()

    assert result["router_info"]["status"] == "connected"
    assert client.logout.called
    client.login.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_data_reuse_path_retries_empty_reused_sessions(
    mock_hass,
) -> None:
    """An empty reused-session response should trigger a one-time reauth."""
    client = _client(
        login=Mock(return_value=True),
        get_devices_response=Mock(
            side_effect=[
                [],
                [
                    {
                        "HostName": "Phone",
                        "IPAddress": "10.0.0.2",
                        "MACAddress": "AA:BB",
                        "Active": True,
                        "NetworkType": "WLAN",
                    }
                ],
            ]
        ),
    )
    client.login_data = {"ok": 1}
    client.session = object()
    coordinator = _make_coordinator(
        mock_hass, _entry(options={CONF_SESSION_REUSE: True}), client
    )
    coordinator._last_login_at = datetime.now()

    result = await coordinator._async_update_data()

    assert result["devices"]["AA:BB"]["name"] == "Phone"
    assert client.login.call_count == 1
    assert client.logout.called


@pytest.mark.asyncio
async def test_async_update_data_reuse_path_returns_unavailable_after_retry_failure(
    mock_hass,
) -> None:
    """Two failed reuse attempts should clear the session and mark unavailable."""
    client = _client(
        login=Mock(return_value=False),
        get_devices_response=Mock(return_value=[]),
    )
    client.login_data = {"ok": 1}
    client.session = object()
    coordinator = _make_coordinator(
        mock_hass, _entry(options={CONF_SESSION_REUSE: True}), client
    )
    coordinator._last_login_at = datetime.now()

    result = await coordinator._async_update_data()

    assert result["router_info"]["status"] == "unavailable"
    assert coordinator.available is False
    assert client.logout.call_count >= 1


def test_legacy_get_scanner_and_control_helpers(mock_hass) -> None:
    """Legacy scanner lookup should return the shared scanner instance."""
    scanner = zteDeviceScanner(
        mock_hass, _client(get_models=Mock(return_value=["F6640"]))
    )
    mock_hass.data = {DOMAIN: {"scanner": scanner}}
    assert get_scanner(mock_hass, {}) is scanner

    scanner.pause()
    assert scanner.scanning is False
    scanner.resume()
    assert scanner.scanning is True


def test_legacy_scanner_handles_success_and_failures(mock_hass) -> None:
    """The legacy scanner should track active devices and safe fallbacks."""
    client = _client(
        get_models=Mock(return_value=["F6640"]),
        get_devices_response=Mock(
            return_value=[
                {
                    "HostName": "Phone",
                    "IPAddress": "10.0.0.2",
                    "MACAddress": "AA:BB",
                    "Active": True,
                    "IconType": "smartphone",
                },
                {
                    "HostName": "Offline",
                    "IPAddress": "10.0.0.3",
                    "MACAddress": "CC:DD",
                    "Active": False,
                },
            ]
        ),
    )
    scanner = zteDeviceScanner(mock_hass, client)

    assert scanner.scan_devices() == ["AA:BB"]
    assert scanner.get_device_name("AA:BB") == "Phone"
    assert scanner.get_device_name("ZZ:ZZ") is None

    scanner.status = "paused"
    assert scanner._get_data() == []

    scanner.status = "on"
    client.login.return_value = False
    assert scanner.scan_devices() == []

    client.login.side_effect = RuntimeError("boom")
    assert scanner._get_data() == []
    assert client.logout.called
