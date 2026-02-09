"""Device tracker platform for ZTE Tracker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
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

    # Ensure router device exists in device registry so child device_tracker entities are attached
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    router_info = (coordinator.data or {}).get("router_info", {}) or {}
    router_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or router_info.get("name", "ZTE Router"),
        manufacturer=router_info.get("manufacturer", "ZTE"),
        model=router_info.get("model"),
    )
    area_id = router_device.area_id

    @callback
    def _async_add_entities():
        """Add device tracker entities for discovered devices."""
        if not coordinator.data:
            return

        data = coordinator.data
        devices = data.get("devices", {})

        entities = []
        allow_new_devices = coordinator.register_new_devices
        for mac, device_data in devices.items():
            # Only create entities for devices that have been seen as active at least once
            if device_data.get("active") or device_data.get("last_seen"):
                unique_id = f"{entry.entry_id}_{mac.replace(':', '_')}"
                # Only add entities that have not been created yet
                found = False
                haentities = async_add_entities.__self__.entities
                for entitykey in haentities:
                    entity = haentities[entitykey]
                    if getattr(entity, "_attr_unique_id", None) == unique_id:
                        # Update entities that have been added to Home Assistant
                        entity._device_data = device_data
                        entity._attr_name = device_data.get("name") or f"Device {mac}"
                        if entity.hass is not None:
                            entity.async_write_ha_state()
                        found = True
                        break
                if not found:
                    # Skip creating new entity if not allowed, unless the entity
                    # already exists in the Home Assistant entity registry.
                    existing_entity_id = entity_registry.async_get_entity_id(
                        "device_tracker", DOMAIN, unique_id
                    )
                    if not allow_new_devices and existing_entity_id is None:
                        # Skip creating new entity when not allowed and no existing registry entry
                        continue
                    entity = ZteDeviceTrackerEntity(
                        coordinator, entry, mac, device_data
                    )
                    entities.append(entity)
                    created_entities.add(mac)

        if entities:
            async_add_entities(entities)
            # Asignar área a las nuevas entidades
            for entity in entities:
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, entity._attr_unique_id
                )
                if entity_id and area_id:
                    entity_registry.async_update_entity(entity_id, area_id=area_id)

    # Add initial entities
    _async_add_entities()

    def _mark_undetected_entities():
        entity_registry = er.async_get(hass)
        for entity_id, entity in entity_registry.entities.items():
            if entity.domain == "device_tracker" and entity.platform == DOMAIN:
                mac = entity.unique_id.split("_")[-1].replace("_", ":")
                devices = (
                    coordinator.data.get("devices", {}) if coordinator.data else {}
                )
                device = devices.get(mac)
                if not device or not device.get("active"):
                    tracker_entity = hass.states.get(entity_id)
                    if tracker_entity:
                        attrs = dict(tracker_entity.attributes)
                        attrs["active"] = False
                        hass.states.async_set(entity_id, "not_home", attrs)

    # Listen for new devices and mark undetected entities after each scan
    def _scan_listener():
        _async_add_entities()
        _mark_undetected_entities()

    coordinator.async_add_listener(_scan_listener)
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

        # Device info is provided via property below

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self._entry.entry_id}_{self._mac.replace(':', '_')}")
            },
            connections={("mac", self._mac)},
            name=self._device_data.get("name") or self._mac,
            manufacturer="ZTE",
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected to the network (active), but do not report as unavailable if not detected."""
        data = self.coordinator.data or {}
        devices = data.get("devices", {})
        device = devices.get(self._mac)
        # If device is not present, keep entity but set active to False
        if device is None:
            return False
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
        network_type = device.get("network_type")
        icon_type = device.get("icon_type")
        # Prefer network_type for icon selection
        if network_type == "LAN":
            return "mdi:lan"
        elif network_type == "WLAN":
            return "mdi:wifi"
        # Fallback to icon_type if available
        if icon_type:
            return ICONS.get(icon_type, "mdi:devices")
        return "mdi:devices"

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
            "port": device.get("port"),
            "link_time": device.get("LinkTime"),
            "connect_time": device.get("ConnectTime"),
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added device tracker for MAC: %s", self._mac)
