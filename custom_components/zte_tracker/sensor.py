"""Sensor platform for ZTE Tracker."""

from __future__ import annotations

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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
            sw_version=coordinator.client.model,
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
        # Get local time in local timezone.
        router_info["last_update"] = ha_dt.now().isoformat()
        return router_info


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
        return {
            "devices": device_list,
            "num_devices": len([d for d in devices.values() if d.get("active")]),
        }
