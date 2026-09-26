"""Tests for the entity platforms."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.device_tracker import SourceType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker import button, device_tracker, sensor, switch
from custom_components.zte_tracker.const import (
    CONF_REGISTER_NEW_DEVICES,
    DOMAIN,
    ICON,
)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry-1",
        title="Main Router",
        data={},
        options={CONF_REGISTER_NEW_DEVICES: True},
    )


def _coordinator(devices: dict | None = None, router_info: dict | None = None):
    coordinator = SimpleNamespace()
    coordinator.client = SimpleNamespace(
        host="192.168.1.1",
        model="F6640",
        base_url="https://192.168.1.1",
        mesh_topology=False,
    )
    coordinator.data = {
        "devices": devices or {},
        "router_info": {
            "status": "connected",
            "ManuFacturer": "ZTE",
            "ModelName": "F6600P",
            "SoftwareVer": "V1.0.0",
            "HardwareVer": "V2.0.0",
            **(router_info or {}),
        },
    }
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_reboot_router = AsyncMock(return_value=True)
    coordinator.pause_scanning = Mock()
    coordinator.resume_scanning = Mock()
    coordinator.register_new_devices = True
    coordinator.enable_register_new_devices = Mock(
        side_effect=lambda: setattr(coordinator, "register_new_devices", True)
    )
    coordinator.disable_register_new_devices = Mock(
        side_effect=lambda: setattr(coordinator, "register_new_devices", False)
    )
    coordinator.paused = False
    return coordinator


class _Collector:
    def __init__(self, entities=None):
        self.entities = entities or {}

    def add_entities(self, entities):
        for index, entity in enumerate(entities, start=len(self.entities)):
            self.entities[f"entity-{index}"] = entity


def _registry_entity(
    *,
    entity_id: str,
    unique_id: str,
    config_entry_id: str = "entry-1",
    disabled_by=None,
    original_name: str | None = None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain="device_tracker",
        platform=DOMAIN,
        unique_id=unique_id,
        config_entry_id=config_entry_id,
        disabled_by=disabled_by,
        original_name=original_name,
        device_id="device-1",
    )


@pytest.mark.asyncio
async def test_button_setup_and_press_paths(mock_hass) -> None:
    """The reboot button should expose success and failure behavior."""
    entry = _entry()
    coordinator = _coordinator()
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    added: list = []

    await button.async_setup_entry(mock_hass, entry, added.extend)

    assert len(added) == 1
    entity = added[0]
    assert entity.name == "ZTE Router 192.168.1.1 Reboot"
    assert entity.unique_id == "entry-1_reboot"
    assert entity.device_info["model"] == "F6640"

    await entity.async_press()
    coordinator.async_reboot_router.assert_awaited_once()

    coordinator.async_reboot_router = AsyncMock(return_value=False)
    with pytest.raises(HomeAssistantError, match="Router reboot failed"):
        await button.ZteRebootButton(coordinator, entry).async_press()

    coordinator.async_reboot_router = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(HomeAssistantError, match="Exception while rebooting"):
        await button.ZteRebootButton(coordinator, entry).async_press()


@pytest.mark.asyncio
async def test_sensor_setup_and_properties(mock_hass) -> None:
    """The sensors should expose router state and device counts."""
    entry = _entry()
    coordinator = _coordinator(
        devices={
            "AA:BB": {
                "name": "Phone",
                "ip": "10.0.0.2",
                "active": True,
            },
            "CC:DD": {
                "name": "Laptop",
                "ip": "10.0.0.3",
                "active": False,
            },
        }
    )
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    added: list = []

    await sensor.async_setup_entry(mock_hass, entry, added.extend)

    assert len(added) == 2
    router_sensor = next(
        entity for entity in added if isinstance(entity, sensor.ZteRouterSensor)
    )
    count_sensor = next(
        entity for entity in added if isinstance(entity, sensor.ZteDeviceCountSensor)
    )

    assert router_sensor.native_value == "connected"
    assert router_sensor.icon == ICON
    assert router_sensor.device_info["configuration_url"] == "https://192.168.1.1"
    with patch(
        "custom_components.zte_tracker.sensor.ha_dt.now",
        return_value=datetime(2026, 1, 1, 10, 30, 0),
    ):
        attrs = router_sensor.extra_state_attributes
    assert attrs["status"] == "connected"
    assert attrs["last_update"] == "2026-01-01T10:30:00"

    assert count_sensor.native_value == 1
    assert count_sensor.extra_state_attributes == {
        "devices": ["AA:BB(Phone-10.0.0.2)", "CC:DD(Laptop-10.0.0.3)"],
        "num_devices": 1,
    }


@pytest.mark.asyncio
async def test_switches_setup_and_toggle_behaviors(mock_hass) -> None:
    """The switches should proxy pause and registration changes."""
    entry = _entry()
    coordinator = _coordinator()
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    added: list = []

    await switch.async_setup_entry(mock_hass, entry, added.extend)

    pause_switch = next(
        entity for entity in added if isinstance(entity, switch.ZtePauseSwitch)
    )
    register_switch = next(
        entity
        for entity in added
        if isinstance(entity, switch.ZteRegisterNewDevicesSwitch)
    )

    assert pause_switch.is_on is False
    coordinator.paused = True
    assert pause_switch.is_on is True
    await pause_switch.async_turn_on()
    await pause_switch.async_turn_off()
    assert coordinator.pause_scanning.called
    assert coordinator.resume_scanning.called
    assert coordinator.async_request_refresh.await_count == 2

    register_switch.hass = mock_hass
    register_switch.async_write_ha_state = Mock()
    mock_hass.config_entries.async_update_entry = Mock()
    assert register_switch.is_on is True

    await register_switch.async_turn_off()
    assert coordinator.disable_register_new_devices.called
    mock_hass.config_entries.async_update_entry.assert_called_with(
        entry, options={CONF_REGISTER_NEW_DEVICES: False}
    )

    await register_switch.async_turn_on()
    assert coordinator.enable_register_new_devices.called
    assert register_switch.async_write_ha_state.call_count == 2


@pytest.mark.asyncio
async def test_register_new_devices_switch_handles_default_and_missing_hass() -> None:
    """The registration switch should keep safe defaults."""
    entry = _entry()
    coordinator = _coordinator()
    delattr(coordinator, "register_new_devices")
    entity = switch.ZteRegisterNewDevicesSwitch(coordinator, entry)

    assert entity.is_on is True
    await entity._async_update_entry_option(False)


def test_device_tracker_entity_exposes_router_link_and_attributes() -> None:
    """Tracker entities should mirror cached device data."""
    entry = _entry()
    coordinator = _coordinator(
        devices={
            "AA:BB": {
                "name": "Phone",
                "ip": "10.0.0.5",
                "active": True,
                "network_type": "WLAN",
                "icon_type": "smartphone",
                "last_seen": "2026-01-01T10:00:00",
                "port": "SSID1",
                "LinkTime": "55",
                "ConnectTime": "2026-01-01T09:59:00",
                "mesh_node": "ZTE:F6600P",
            }
        }
    )
    entity = device_tracker.ZteDeviceTrackerEntity(
        coordinator, entry, "AA:BB", {"name": "Phone"}, "router-device-id"
    )

    via_key = (
        "via_device_id" if device_tracker._SUPPORTS_VIA_DEVICE_ID else "via_device"
    )
    expected_via = (
        "router-device-id"
        if device_tracker._SUPPORTS_VIA_DEVICE_ID
        else (DOMAIN, "entry-1")
    )
    assert entity.device_info["connections"] == {("mac", "AA:BB")}
    assert entity.device_info[via_key] == expected_via
    assert entity.source_type is SourceType.ROUTER
    assert entity.is_connected is True
    assert entity.ip_address == "10.0.0.5"
    assert entity.hostname == "Phone"
    assert entity.icon == "mdi:wifi"
    assert entity.extra_state_attributes["mesh_node"] == "ZTE:F6600P"

    coordinator.data["devices"] = {"AA:BB": {"network_type": "LAN"}}
    assert entity.icon == "mdi:lan"
    coordinator.data["devices"] = {"AA:BB": {"icon_type": "unknown"}}
    assert entity.icon == "mdi:devices"
    coordinator.data["devices"] = {}
    assert entity.is_connected is False
    assert entity.ip_address is None
    assert entity.hostname is None


@pytest.mark.asyncio
async def test_device_tracker_entity_added_to_hass_delegates_to_parent() -> None:
    """The entity should still call the coordinator base hook."""
    entry = _entry()
    entity = device_tracker.ZteDeviceTrackerEntity(
        _coordinator(), entry, "AA:BB", {"name": "Phone"}
    )

    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
        AsyncMock(),
    ) as parent_added:
        await entity.async_added_to_hass()

    parent_added.assert_awaited_once()


@pytest.mark.asyncio
async def test_device_tracker_setup_creates_entities_and_assigns_area(
    mock_hass,
) -> None:
    """A fresh scan should create entities under the router area."""
    entry = _entry()
    coordinator = _coordinator(
        devices={
            "AA:BB": {
                "name": "Phone",
                "ip": "10.0.0.5",
                "active": True,
                "last_seen": "2026-01-01T10:00:00",
            }
        },
        router_info={"name": "Configured Router"},
    )
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    collector = _Collector()
    device_registry = Mock()
    device_registry.async_get_or_create.return_value = SimpleNamespace(
        id="router-device-id", area_id="office"
    )
    entity_registry = Mock()
    entity_registry.entities = {}
    entity_registry.async_get_entity_id.side_effect = (
        lambda domain, platform, unique_id: (
            "device_tracker.phone" if unique_id == "AA:BB" else None
        )
    )
    entity_registry.async_update_entity = Mock()

    with (
        patch(
            "custom_components.zte_tracker.device_tracker.dr.async_get",
            return_value=device_registry,
        ),
        patch(
            "custom_components.zte_tracker.device_tracker.er.async_get",
            return_value=entity_registry,
        ),
    ):
        await device_tracker.async_setup_entry(mock_hass, entry, collector.add_entities)

    assert len(collector.entities) == 1
    created = next(iter(collector.entities.values()))
    assert isinstance(created, device_tracker.ZteDeviceTrackerEntity)
    assert created.mac_address == "AA:BB"
    device_registry.async_get_or_create.assert_called_once()
    entity_registry.async_update_entity.assert_called_once_with(
        "device_tracker.phone", area_id="office"
    )
    assert coordinator.async_add_listener.call_count == 2


@pytest.mark.asyncio
async def test_device_tracker_setup_respects_registration_flag(mock_hass) -> None:
    """New devices should be skipped when registration is disabled."""
    entry = _entry()
    coordinator = _coordinator(
        devices={"AA:BB": {"name": "Phone", "active": True, "last_seen": "now"}}
    )
    coordinator.register_new_devices = False
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    collector = _Collector()
    device_registry = Mock()
    device_registry.async_get_or_create.return_value = SimpleNamespace(
        id="router-device-id", area_id=None
    )
    entity_registry = Mock()
    entity_registry.entities = {}
    entity_registry.async_get_entity_id.return_value = None

    with (
        patch(
            "custom_components.zte_tracker.device_tracker.dr.async_get",
            return_value=device_registry,
        ),
        patch(
            "custom_components.zte_tracker.device_tracker.er.async_get",
            return_value=entity_registry,
        ),
    ):
        await device_tracker.async_setup_entry(mock_hass, entry, collector.add_entities)

    assert collector.entities == {}


@pytest.mark.asyncio
async def test_device_tracker_setup_recreates_registry_entities_and_marks_them_offline(
    mock_hass,
) -> None:
    """Registry devices should survive restarts and missing scans."""
    entry = _entry()
    coordinator = _coordinator(devices={})
    coordinator.register_new_devices = False
    mock_hass.data = {DOMAIN: {entry.entry_id: coordinator}}
    mock_hass.states = SimpleNamespace(
        get=Mock(
            return_value=SimpleNamespace(
                attributes={"friendly_name": "Known Phone", "active": True}
            )
        ),
        async_set=Mock(),
    )
    collector = _Collector()
    device_registry = Mock()
    device_registry.async_get_or_create.return_value = SimpleNamespace(
        id="router-device-id", area_id=None
    )
    registry_entity = _registry_entity(
        entity_id="device_tracker.known_phone",
        unique_id="AA:BB",
        original_name="Known Phone",
    )
    disabled_entity = _registry_entity(
        entity_id="device_tracker.disabled",
        unique_id="CC:DD",
        disabled_by="user",
    )
    entity_registry = Mock()
    entity_registry.entities = {
        "device_tracker.known_phone": registry_entity,
        "device_tracker.disabled": disabled_entity,
    }
    entity_registry.async_get_entity_id.return_value = None

    with (
        patch(
            "custom_components.zte_tracker.device_tracker.dr.async_get",
            return_value=device_registry,
        ),
        patch(
            "custom_components.zte_tracker.device_tracker.er.async_get",
            return_value=entity_registry,
        ),
    ):
        await device_tracker.async_setup_entry(mock_hass, entry, collector.add_entities)
        assert len(collector.entities) == 1
        restored = next(iter(collector.entities.values()))
        assert restored.name == "Known Phone"
        assert restored.device_info["name"] == "Known Phone"

        scan_listener = coordinator.async_add_listener.call_args_list[0].args[0]
        scan_listener()

        assert mock_hass.states.async_set.call_count == 2
        mock_hass.states.async_set.assert_any_call(
            "device_tracker.known_phone",
            "not_home",
            {"friendly_name": "Known Phone", "active": False},
        )
