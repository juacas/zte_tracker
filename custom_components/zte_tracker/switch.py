"""Switch platform for ZTE Tracker."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REGISTER_NEW_DEVICES, DOMAIN
from .coordinator import ZteDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE tracker switches from config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ZtePauseSwitch(coordinator, entry),
            ZteRegisterNewDevicesSwitch(coordinator, entry),
        ]
    )


class ZtePauseSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to pause/resume the tracker."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "ZTE Tracker Pause"
        self._attr_unique_id = f"{entry.entry_id}_pause_switch"
        self._attr_icon = "mdi:pause-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
        )

    @property
    def is_on(self) -> bool:
        """Return True if tracker is paused."""
        # Ensure coordinator is ZteDataCoordinator
        if hasattr(self.coordinator, "paused"):
            return self.coordinator.paused
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Pause the tracker."""
        if hasattr(self.coordinator, "pause_scanning"):
            self.coordinator.pause_scanning()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Resume the tracker."""
        if hasattr(self.coordinator, "resume_scanning"):
            self.coordinator.resume_scanning()
            await self.coordinator.async_request_refresh()


class ZteRegisterNewDevicesSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control registration of new devices."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "ZTE Register New Devices"
        self._attr_unique_id = f"{entry.entry_id}_register_new_devices"
        self._attr_icon = "mdi:lan-connect"
        self._default_register = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
        )

    @property
    def is_on(self) -> bool:
        """Return True if new devices will be registered."""
        if hasattr(self.coordinator, "register_new_devices"):
            return self.coordinator.register_new_devices
        return self._default_register

    async def _async_update_entry_option(self, enabled: bool) -> None:
        """Persist the register new devices option in the config entry."""
        if not self.hass or not hasattr(self.hass, "config_entries"):
            return
        current = self._entry.options.get(
            CONF_REGISTER_NEW_DEVICES, self._default_register
        )
        if current == enabled:
            return
        updated_options = dict(self._entry.options)
        updated_options[CONF_REGISTER_NEW_DEVICES] = enabled
        self.hass.config_entries.async_update_entry(
            self._entry, options=updated_options
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable registration of new devices."""
        self.coordinator.enable_register_new_devices()
        await self._async_update_entry_option(True)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable registration of new devices."""
        self.coordinator.disable_register_new_devices()
        await self._async_update_entry_option(False)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
