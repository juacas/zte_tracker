"""Device tracker platform for ZTE Tracker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    # Obtener el área del dispositivo ZTERouter
    device_registry = hass.data.get("device_registry")
    entity_registry = er.async_get(hass)
    zte_device = None
    area_id = None
    # Buscar el dispositivo ZTERouter por entry_id
    if device_registry:
        for dev in device_registry.devices.values():
            if entry.entry_id in dev.identifiers:
                zte_device = dev
                area_id = dev.area_id
                break

    @callback
    def _async_add_entities():
        """Add device tracker entities for discovered devices."""
        if not coordinator.data:
            return

        data = coordinator.data
        devices = data.get("devices", {})

        entities = []
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

    from homeassistant.helpers import config_validation as cv
    import voluptuous as vol

    REMOVE_TRACKED_ENTITY_SCHEMA = vol.Schema(
        {
            vol.Required("mac"): cv.string,
        }
    )

    async def async_remove_tracked_entity(call):
        """
        Remove a tracked device entity by MAC address.

        Service data:
          mac: MAC address of the device to remove (string, required)
        """
        mac = call.data.get("mac")
        if not mac:
            _LOGGER.error("No MAC address provided for removal.")
            return
        unique_id = f"{entry.entry_id}_{mac.replace(':', '_')}"
        # Remove entity using entity registry
        entity_registry = er.async_get(hass)
        entity_id = entity_registry.async_get_entity_id(
            "device_tracker", DOMAIN, unique_id
        )
        if entity_id:
            entity_registry.async_remove(entity_id)
            _LOGGER.info("Removed tracked entity for MAC: %s", mac)
        else:
            _LOGGER.warning("No entity found for MAC: %s", mac)

    # Register service to remove tracked entities
    hass.services.async_register(
        DOMAIN,
        "remove_tracked_entity",
        async_remove_tracked_entity,
        schema=REMOVE_TRACKED_ENTITY_SCHEMA,
    )


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
        unique_id = (
            str(self._attr_unique_id) if self._attr_unique_id is not None else ""
        )
        return DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=self._attr_name,
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
