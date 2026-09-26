"""Tests for integration setup, services, and unload behavior."""

from __future__ import annotations

import asyncio
import custom_components.zte_tracker as zte_init
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker.const import (
    CONF_MESH_TOPOLOGY,
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    CONF_SESSION_REUSE,
    DEFAULT_MESH_TOPOLOGY,
    DOMAIN,
    PLATFORMS,
)


def _entry(data=None, options=None, **kwargs) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=kwargs.pop("entry_id", "entry-1"),
        title="ZTE Router",
        data={
            CONF_HOST: "192.168.1.1",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            CONF_MODEL: "F6640",
            **(data or {}),
        },
        options=options or {},
        **kwargs,
    )
    entry.add_update_listener = Mock(side_effect=lambda callback: callback)
    entry.async_on_unload = Mock()
    return entry


def _hass(mock_hass):
    mock_hass.data = {}
    mock_hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    mock_hass.services = SimpleNamespace()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    mock_hass.config_entries.async_schedule_reload = Mock()
    mock_hass.config_entries.async_update_entry = Mock()
    mock_hass.services.has_service = Mock(return_value=False)
    mock_hass.services.async_register = Mock()
    mock_hass.auth = SimpleNamespace(async_get_user=AsyncMock())
    mock_hass.config = SimpleNamespace(path=lambda *parts: "/tmp/" + "/".join(parts))
    return mock_hass


def _coordinator():
    coordinator = SimpleNamespace()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator._client_lock = asyncio.Lock()
    coordinator._reuse_session = False
    coordinator._mesh_topology = False
    coordinator._last_login_at = "sentinel"
    coordinator.client = SimpleNamespace(
        host="192.168.1.1",
        mesh_topology=False,
        query_wan_status=True,
        query_router_details=True,
        logout=Mock(),
    )
    coordinator.async_reboot_router = AsyncMock(return_value=True)
    return coordinator


def _call(hass, data=None, user_id=None):
    return SimpleNamespace(
        hass=hass,
        data=data or {},
        context=SimpleNamespace(user_id=user_id),
    )


@pytest.mark.asyncio
async def test_async_setup_tracks_legacy_yaml_config(mock_hass) -> None:
    """Legacy YAML config should be kept for migration."""
    hass = _hass(mock_hass)

    assert await zte_init.async_setup(hass, {DOMAIN: {"host": "192.168.1.1"}}) is True
    assert hass.data[DOMAIN]["yaml_config"] == {"host": "192.168.1.1"}


@pytest.mark.asyncio
async def test_async_setup_without_yaml_still_initializes_domain_data(
    mock_hass,
) -> None:
    """The domain store should exist even without YAML config."""
    hass = _hass(mock_hass)

    assert await zte_init.async_setup(hass, {}) is True
    assert hass.data[DOMAIN] == {}


@pytest.mark.asyncio
async def test_async_setup_entry_migrates_legacy_flags_and_registers_services(
    mock_hass,
) -> None:
    """Entry setup should migrate legacy data keys and register services once."""
    hass = _hass(mock_hass)
    entry = _entry(
        data={
            CONF_QUERY_WAN_STATUS: False,
            CONF_QUERY_ROUTER_DETAILS: False,
            CONF_SESSION_REUSE: True,
        },
        options={},
    )
    coordinator = _coordinator()

    with (
        patch(
            "custom_components.zte_tracker.ZteDataCoordinator", return_value=coordinator
        ),
        patch("custom_components.zte_tracker.setup_services") as setup_services,
    ):
        result = await zte_init.async_setup_entry(hass, entry)

    assert result is True
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        data={
            CONF_HOST: "192.168.1.1",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            CONF_MODEL: "F6640",
        },
        options={
            CONF_QUERY_WAN_STATUS: False,
            CONF_QUERY_ROUTER_DETAILS: False,
            CONF_SESSION_REUSE: True,
        },
    )
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )
    setup_services.assert_called_once_with(hass)
    entry.add_update_listener.assert_called_once()
    entry.async_on_unload.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_ignores_migration_errors(mock_hass) -> None:
    """A migration failure should not block the integration from loading."""
    hass = _hass(mock_hass)
    hass.config_entries.async_update_entry.side_effect = RuntimeError("boom")
    hass.services.has_service.return_value = True
    entry = _entry(data={CONF_QUERY_WAN_STATUS: False})
    coordinator = _coordinator()

    with patch(
        "custom_components.zte_tracker.ZteDataCoordinator", return_value=coordinator
    ):
        result = await zte_init.async_setup_entry(hass, entry)

    assert result is True
    coordinator.async_config_entry_first_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_options_listener_schedules_reload_for_session_reuse_changes(
    mock_hass,
) -> None:
    """Changing session reuse should short-circuit to a reload."""
    hass = _hass(mock_hass)
    entry = _entry()
    coordinator = _coordinator()

    with patch(
        "custom_components.zte_tracker.ZteDataCoordinator", return_value=coordinator
    ):
        await zte_init.async_setup_entry(hass, entry)

    listener = entry.add_update_listener.call_args.args[0]
    updated = _entry(options={CONF_SESSION_REUSE: True}, entry_id=entry.entry_id)

    await listener(hass, updated)

    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)
    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_options_listener_updates_client_and_refreshes(mock_hass) -> None:
    """Mesh and query toggles should update the live client before refresh."""
    hass = _hass(mock_hass)
    entry = _entry()
    coordinator = _coordinator()

    with patch(
        "custom_components.zte_tracker.ZteDataCoordinator", return_value=coordinator
    ):
        await zte_init.async_setup_entry(hass, entry)

    listener = entry.add_update_listener.call_args.args[0]
    updated = _entry(
        options={
            CONF_QUERY_WAN_STATUS: False,
            CONF_QUERY_ROUTER_DETAILS: False,
            CONF_SESSION_REUSE: False,
            CONF_MESH_TOPOLOGY: True,
        },
        entry_id=entry.entry_id,
    )

    await listener(hass, updated)

    assert coordinator.client.query_wan_status is False
    assert coordinator.client.query_router_details is False
    assert coordinator.client.mesh_topology is True
    coordinator.client.logout.assert_called_once()
    assert coordinator._last_login_at is None
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_options_listener_schedules_reload_when_refresh_fails(mock_hass) -> None:
    """Refresh failures after an options change should fall back to reload."""
    hass = _hass(mock_hass)
    entry = _entry()
    coordinator = _coordinator()
    coordinator.async_request_refresh.side_effect = RuntimeError("refresh failed")

    with patch(
        "custom_components.zte_tracker.ZteDataCoordinator", return_value=coordinator
    ):
        await zte_init.async_setup_entry(hass, entry)

    listener = entry.add_update_listener.call_args.args[0]
    updated = _entry(
        options={CONF_MESH_TOPOLOGY: DEFAULT_MESH_TOPOLOGY},
        entry_id=entry.entry_id,
    )

    await listener(hass, updated)

    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_async_unload_entry_closes_client_session(mock_hass) -> None:
    """Unloading should log out the live client and drop stored coordinator data."""
    hass = _hass(mock_hass)
    entry = _entry()
    coordinator = _coordinator()
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    assert await zte_init.async_unload_entry(hass, entry) is True
    coordinator.client.logout.assert_called_once()
    assert hass.data[DOMAIN] == {}


@pytest.mark.asyncio
async def test_async_unload_entry_ignores_logout_errors(mock_hass) -> None:
    """Logout failures should not make unload fail."""
    hass = _hass(mock_hass)
    entry = _entry()
    coordinator = _coordinator()
    coordinator.client.logout.side_effect = RuntimeError("boom")
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    assert await zte_init.async_unload_entry(hass, entry) is True


@pytest.mark.asyncio
async def test_async_reboot_service_filters_by_host_and_raises_when_nothing_rebooted(
    mock_hass,
) -> None:
    """The reboot service should support host targeting and empty results."""
    hass = _hass(mock_hass)
    coord_a = _coordinator()
    coord_b = _coordinator()
    coord_b.client.host = "10.0.0.2"
    coord_b.async_reboot_router = AsyncMock(return_value=False)
    hass.data[DOMAIN] = {"a": coord_a, "b": coord_b, "yaml_config": {}}

    await zte_init.async_reboot_service(_call(hass, {"host": "192.168.1.1"}))
    coord_a.async_reboot_router.assert_awaited_once()
    coord_b.async_reboot_router.assert_not_awaited()

    with pytest.raises(HomeAssistantError, match="No routers rebooted"):
        await zte_init.async_reboot_service(_call(hass, {"host": "10.0.0.2"}))


@pytest.mark.asyncio
async def test_async_remove_tracked_entity_removes_orphan_devices(mock_hass) -> None:
    """Removing a tracked entity should also remove its orphaned device."""
    hass = _hass(mock_hass)
    entity_registry = Mock()
    entity_registry.entities = {
        "device_tracker.phone": SimpleNamespace(
            domain="device_tracker",
            platform=DOMAIN,
            unique_id="AA:BB:CC:DD:EE:FF",
            device_id="device-1",
        )
    }
    entity_registry.async_remove = Mock(
        side_effect=lambda entity_id: entity_registry.entities.pop(entity_id, None)
    )
    device_registry = Mock()
    device_registry.async_remove_device = Mock()

    with (
        patch(
            "custom_components.zte_tracker.er.async_get", return_value=entity_registry
        ),
        patch(
            "custom_components.zte_tracker.dr.async_get", return_value=device_registry
        ),
    ):
        await zte_init.async_remove_tracked_entity(
            _call(hass, {"mac": "aa-bb-cc-dd-ee-ff"})
        )

    entity_registry.async_remove.assert_called_once_with("device_tracker.phone")
    device_registry.async_remove_device.assert_called_once_with("device-1")


@pytest.mark.asyncio
async def test_async_remove_tracked_entity_handles_missing_and_empty_mac(
    mock_hass,
) -> None:
    """Missing MAC input should no-op and unmatched MACs should raise."""
    hass = _hass(mock_hass)
    entity_registry = Mock()
    entity_registry.entities = {}

    with patch(
        "custom_components.zte_tracker.er.async_get", return_value=entity_registry
    ):
        await zte_init.async_remove_tracked_entity(_call(hass, {}))
        with pytest.raises(HomeAssistantError, match="No entity found"):
            await zte_init.async_remove_tracked_entity(
                _call(hass, {"mac": "AA:BB:CC:DD:EE:FF"})
            )


@pytest.mark.asyncio
async def test_async_remove_unidentified_entities_service(mock_hass) -> None:
    """Only unidentified device trackers should be removed."""
    hass = _hass(mock_hass)
    entity_registry = Mock()
    entity_registry.entities = {
        "device_tracker.keep": SimpleNamespace(domain="device_tracker", unique_id="AA"),
        "device_tracker.drop": SimpleNamespace(domain="device_tracker", unique_id=None),
    }
    entity_registry.async_remove = Mock()

    with patch(
        "custom_components.zte_tracker.er.async_get", return_value=entity_registry
    ):
        await zte_init.async_remove_unidentified_entities_service(_call(hass))

    entity_registry.async_remove.assert_called_once_with("device_tracker.drop")


@pytest.mark.asyncio
async def test_export_support_bundle_requires_admin_and_acknowledgement(
    mock_hass,
) -> None:
    """The export service should enforce admin and acknowledgement checks."""
    hass = _hass(mock_hass)
    hass.auth.async_get_user.return_value = SimpleNamespace(is_admin=False)

    with pytest.raises(Unauthorized):
        await zte_init.async_export_support_bundle_service(
            _call(hass, {"acknowledge_sensitive_data": True}, user_id="user-1")
        )

    with pytest.raises(HomeAssistantError, match="acknowledge_sensitive_data"):
        await zte_init.async_export_support_bundle_service(
            _call(hass, {"acknowledge_sensitive_data": False})
        )


@pytest.mark.asyncio
async def test_export_support_bundle_handles_error_only_and_successful_walks(
    mock_hass,
) -> None:
    """Exports should include both probe failures and written bundle metadata."""
    hass = _hass(mock_hass)
    coord_error = _coordinator()
    coord_ok = _coordinator()
    coord_ok.client.host = "10.0.0.2"
    hass.data[DOMAIN] = {"error": coord_error, "ok": coord_ok}

    bundles = [
        {"error": "login failed", "preauth": {}},
        {
            "reported": {"profile": "F6640"},
            "probes": {"a": {"status": 200}, "b": {"status": 404}},
            "walk_truncated": True,
            "preauth_truncated": False,
        },
    ]

    with (
        patch("custom_components.zte_tracker._prune_old_bundles"),
        patch("custom_components.zte_tracker.build_bundle", side_effect=bundles),
        patch("custom_components.zte_tracker._write_bundle") as write_bundle,
        patch("custom_components.zte_tracker.datetime") as fake_datetime,
        patch("custom_components.zte_tracker.secrets.token_hex", return_value="abc123"),
    ):
        fake_datetime.now.return_value.strftime.return_value = "20260101-101010-000001"
        result = await zte_init.async_export_support_bundle_service(
            _call(hass, {"acknowledge_sensitive_data": True})
        )

    assert result["bundles"]["192.168.1.1"] == {"error": "login failed"}
    assert (
        result["bundles"]["10.0.0.2"]["file"]
        == "zte_tracker_support/export-abc123-20260101-101010-000001.json"
    )
    assert result["bundles"]["10.0.0.2"]["probes_total"] == 2
    assert result["bundles"]["10.0.0.2"]["probes_ok"] == 1
    assert result["bundles"]["10.0.0.2"]["truncated"] is True
    write_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_export_support_bundle_raises_when_no_router_matches(mock_hass) -> None:
    """A host filter with no matches should fail clearly."""
    hass = _hass(mock_hass)
    hass.data[DOMAIN] = {}

    with pytest.raises(HomeAssistantError, match="No ZTE router found"):
        await zte_init.async_export_support_bundle_service(
            _call(hass, {"acknowledge_sensitive_data": True, "host": "10.0.0.2"})
        )


def test_setup_services_registers_all_service_handlers(mock_hass) -> None:
    """Service registration should wire every public handler."""
    hass = _hass(mock_hass)

    zte_init.setup_services(hass)

    assert hass.services.async_register.call_count == 4
    register_calls = hass.services.async_register.call_args_list
    assert register_calls[-1].kwargs["supports_response"] is SupportsResponse.OPTIONAL
