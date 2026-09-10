"""Device tracker platform for ZTE Tracker."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICONS
from .coordinator import ZteDataCoordinator

# HA deprecated the via_device parameter in favour of via_device_id, and says
# so at runtime; it stops working in 2027.8. via_device_id does not exist on
# the older cores this integration still supports, so pick at import time
# rather than hardcoding either one.
_SUPPORTS_VIA_DEVICE_ID = "via_device_id" in getattr(DeviceInfo, "__annotations__", {})

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
    client = getattr(coordinator, "client", None)
    # ModelName, HardwareVer and SoftwareVer come from the OBJ_DEVINFO_ID node
    # the client now reads. Before this, the device card showed the configured
    # profile name in the firmware field, so a user checking their firmware
    # version was told "F6600P".
    router_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or router_info.get("name", "ZTE Router"),
        manufacturer=router_info.get("ManuFacturer")
        or router_info.get("manufacturer", "ZTE"),
        model=router_info.get("ModelName") or router_info.get("model"),
        sw_version=router_info.get("SoftwareVer"),
        hw_version=router_info.get("HardwareVer"),
        configuration_url=getattr(client, "base_url", None),
    )
    area_id = router_device.area_id

    @callback
    def _async_add_entities():
        """Add device tracker entities for discovered devices."""
        if not coordinator.data:
            return

        data = coordinator.data
        devices = data.get("devices", {})

        entities: list[ZteDeviceTrackerEntity] = []
        allow_new_devices = coordinator.register_new_devices

        # Current entity objects in hass (entity_id -> entity object)
        haentities = async_add_entities.__self__.entities

        # IMPORTANT: ScannerEntity (homeassistant.components.device_tracker
        # .config_entry.ScannerEntity) overrides the `unique_id` property to
        # always return `self.mac_address`, regardless of what
        # `self._attr_unique_id` is set to. So the *effective* unique_id for
        # every entity here is simply the MAC address itself (as returned by
        # `mac_address`) - never an entry_id-prefixed string. All matching
        # below is done on that basis.

        # Create/update entities for devices found in the latest scan
        for mac, device_data in devices.items():
            # Only create entities for devices that have been seen as active at least once
            if device_data.get("active") or device_data.get("last_seen"):
                # Only add entities that have not been created yet
                found = False
                for entitykey in haentities:
                    entity = haentities[entitykey]
                    if getattr(entity, "mac_address", None) == mac:
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
                        "device_tracker", DOMAIN, mac
                    )
                    if not allow_new_devices and existing_entity_id is None:
                        # Skip creating new entity when not allowed and no existing registry entry
                        continue
                    entity = ZteDeviceTrackerEntity(
                        coordinator, entry, mac, device_data, router_device.id
                    )
                    entities.append(entity)
                    created_entities.add(mac)

        # Recreate entities present in the entity registry for this config entry
        # even if the device is currently absent from the scan (e.g. right after
        # a HA restart, before the device has reconnected). Skip disabled entries.
        #
        # NOTE: also track MACs queued in *this* invocation (from the loop
        # above) so we don't create a second, duplicate entity for a device
        # that is both in the current scan AND already in the entity registry
        # - `haentities` only reflects entities already added to hass in a
        # *previous* call, not ones still pending in the local `entities` list.
        queued_macs = {e.mac_address for e in entities}
        for reg_entity in list(entity_registry.entities.values()):
            # Skip disabled entities in the registry (user/automation disabled)
            if getattr(reg_entity, "disabled_by", None) is not None:
                continue

            if (
                reg_entity.domain != "device_tracker"
                or reg_entity.platform != DOMAIN
                or getattr(reg_entity, "config_entry_id", None) != entry.entry_id
            ):
                continue

            # unique_id IS the MAC address for a ScannerEntity - see note above.
            reg_mac = reg_entity.unique_id
            if not reg_mac:
                continue

            if reg_mac in queued_macs:
                continue

            # If an entity object is already present, skip
            already_present = any(
                getattr(haentities[entitykey], "mac_address", None) == reg_mac
                for entitykey in haentities
            )
            if already_present:
                continue

            # Create entity with available device data (may be empty/offline)
            device_data = devices.get(reg_mac)
            if not device_data:
                # The device is offline upon restart.
                # Create an empty dict but retrieve the historical name from the registry
                # to prevent it from being overwritten with the "Device {mac}" fallback.
                device_data = {}
                if getattr(reg_entity, "original_name", None):
                    device_data["name"] = reg_entity.original_name

            entity = ZteDeviceTrackerEntity(
                coordinator, entry, reg_mac, dict(device_data), router_device.id
            )
            entities.append(entity)
            queued_macs.add(reg_mac)
            created_entities.add(reg_mac)

        if entities:
            async_add_entities(entities)
            # Assign area to the new entities
            for entity in entities:
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, entity.mac_address
                )
                if entity_id and area_id:
                    entity_registry.async_update_entity(entity_id, area_id=area_id)

    # Add initial entities
    _async_add_entities()

    def _mark_undetected_entities():
        entity_registry = er.async_get(hass)
        for entity_id, entity in entity_registry.entities.items():
            if entity.domain == "device_tracker" and entity.platform == DOMAIN:
                # unique_id IS the MAC address for a ScannerEntity - see note
                # in _async_add_entities above. No entry_id prefix is ever
                # involved, regardless of what _attr_unique_id was set to.
                mac = entity.unique_id
                if not mac:
                    continue
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
        router_device_id: str | None = None,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._entry = entry
        self._mac = mac
        self._device_data = device_data
        self._router_device_id = router_device_id
        self._attr_name = device_data.get("name") or f"Device {mac}"

        # NOTE: we intentionally do NOT set self._attr_unique_id here. HA's
        # ScannerEntity base class (homeassistant/components/device_tracker/
        # config_entry.py) overrides the `unique_id` property to always
        # return `self.mac_address` - any `_attr_unique_id` we set would be
        # silently ignored. The real unique_id is the `mac_address` property
        # below, i.e. `self._mac` as-is (whatever case the router reports).
        _LOGGER.debug(
            "ZteDeviceTrackerEntity created: mac=%s (effective unique_id, "
            "per ScannerEntity.unique_id -> mac_address)",
            mac,
        )

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
            **self._via_router(),
        )

    def _via_router(self) -> dict[str, Any]:
        """Link this device to the router, on whichever key HA accepts."""
        if _SUPPORTS_VIA_DEVICE_ID and self._router_device_id:
            return {"via_device_id": self._router_device_id}
        return {"via_device": (DOMAIN, self._entry.entry_id)}

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
            "mesh_node": device.get("mesh_node"),
        }

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added device tracker for MAC: %s", self._mac)
