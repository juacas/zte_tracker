"""Sensor platform for ZTE Tracker."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as ha_dt

from .const import DOMAIN, ICON
from .coordinator import ZteDataCoordinator
from .zteclient.zte_client import cmcc_wifi_clients


# The recorder drops the whole attribute set of a state above 16384 bytes
# (homeassistant.components.recorder.db_schema.MAX_STATE_ATTRS_BYTES). Stay below it with
# room for the attributes Home Assistant adds itself (friendly_name, icon, unit).
_MAX_ATTRIBUTES_BYTES = 15000


def _json_size(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())


def _add_clients(attributes: dict[str, Any], clients: list[dict]) -> None:
    """Add as many ``clients`` as fit under _MAX_ATTRIBUTES_BYTES; flag the cut with ``clients_truncated``."""
    used = _json_size({**attributes, "clients": [], "clients_truncated": True})
    fitted: list[dict] = []
    for client in clients:
        used += _json_size(client) + 1  # +1: the comma between list items
        if used > _MAX_ATTRIBUTES_BYTES:
            attributes["clients_truncated"] = True
            break
        fitted.append(client)
    attributes["clients"] = fitted


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE sensor from config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ZteRouterSensor(coordinator, entry),
            ZteDeviceCountSensor(coordinator, entry),
        ]
    )


class ZteBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for ZTE sensors."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        router_info = (coordinator.data or {}).get("router_info", {}) or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer=router_info.get("ManuFacturer", "ZTE"),
            model=router_info.get("ModelName") or coordinator.client.model,
            sw_version=router_info.get("SoftwareVer"),
            hw_version=router_info.get("HardwareVer"),
            # The scheme is per profile and the user can override it, so the
            # link is taken from the client rather than assumed. It was
            # hardcoded to https, which is a dead link on an http only unit.
            configuration_url=getattr(coordinator.client, "base_url", None),
        )


class ZteRouterSensor(ZteBaseSensor):
    """Sensor representing the router status."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the router sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"ZTE Router {coordinator.client.host}"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = ICON

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        return router_info.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data or {}
        router_info = data.get("router_info", {})
        # Return a copy to avoid mutating shared coordinator.data
        interval = self.coordinator.update_interval
        return {
            **router_info,
            "last_update": ha_dt.now().isoformat(),
            "poll_interval": int(interval.total_seconds()) if interval else None,
        }


class ZteDeviceCountSensor(ZteBaseSensor):
    """Sensor for the number of connected devices."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the device count sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"ZTE Router {coordinator.client.host} Connected Devices"
        self._attr_unique_id = f"{entry.entry_id}_device_count"
        self._attr_icon = "mdi:devices"
        self._attr_native_unit_of_measurement = "devices"

    @property
    def native_value(self) -> int:
        """Return the number of connected devices."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        return len([d for d in devices.values() if d.get("active")])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes, including the list of detected devices."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device_list = [
            f"{mac}({device.get('name', 'Unknown')}-{device.get('ip', '')})"
            for mac, device in devices.items()
        ]
        attributes: dict[str, Any] = {
            "devices": device_list,
            "num_devices": len([d for d in devices.values() if d.get("active")]),
        }
        if self.coordinator.client.paths.get("login_style") == "cmcc_form":
            # E2633 only: active WiFi clients with band, signal and rates, cut to fit the recorder limit.
            _add_clients(attributes, cmcc_wifi_clients(devices))
        return attributes
