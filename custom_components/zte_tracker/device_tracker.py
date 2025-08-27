"""Device tracker platform for ZTE Tracker."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICONS
from .coordinator import ZteDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE device tracker from config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Track entities we've already created
    created_entities = set()
    
    @callback
    def _async_add_entities():
        """Add device tracker entities for discovered devices."""
        if not coordinator.data:
            return
            
        data = coordinator.data
        devices = data.get("devices", {})
        
        entities = []
        for mac, device_data in devices.items():
            if mac in created_entities:
                continue
                
            # Only create entities for devices that have been seen as active at least once
            if device_data.get("active") or device_data.get("last_seen"):
                entity = ZteDeviceTrackerEntity(coordinator, entry, mac, device_data)
                entities.append(entity)
                created_entities.add(mac)
        
        if entities:
            async_add_entities(entities)
    
    # Add initial entities
    _async_add_entities()
    
    # Listen for new devices
    coordinator.async_add_listener(_async_add_entities)


class ZteDeviceTrackerEntity(CoordinatorEntity, ScannerEntity):
    """Representation of a ZTE tracked device."""

    def __init__(
        self,
        coordinator: ZteDataCoordinator,
        entry: ConfigEntry,
        mac: str,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._entry = entry
        self._mac = mac
        self._device_data = device_data
        
        # Generate unique ID and name
        self._attr_unique_id = f"{entry.entry_id}_{mac.replace(':', '_')}"
        self._attr_name = device_data.get("name") or f"Device {mac}"
        
        # Set up device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac, {})
        return device.get("active", False)

    @property
    def ip_address(self) -> str | None:
        """Return the IP address of the device."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac, {})
        return device.get("ip")

    @property
    def mac_address(self) -> str:
        """Return the MAC address of the device."""
        return self._mac

    @property
    def hostname(self) -> str | None:
        """Return the hostname of the device."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac, {})
        return device.get("name")

    @property
    def icon(self) -> str | None:
        """Return the icon for the device."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac, {})
        icon_type = device.get("icon_type")
        return ICONS.get(icon_type) if icon_type else "mdi:devices"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac, {})
        
        return {
            "mac_address": self._mac,
            "ip_address": device.get("ip"),
            "hostname": device.get("name"),
            "network_type": device.get("network_type"),
            "icon_type": device.get("icon_type"),
            "last_seen": device.get("last_seen"),
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added device tracker for MAC: %s", self._mac)
