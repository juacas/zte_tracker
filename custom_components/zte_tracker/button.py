"""Button platform for ZTE Tracker to reboot the router."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZteDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the ZTE reboot button for a config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([ZteRebootButton(coordinator, entry)])


class ZteRebootButton(CoordinatorEntity, ButtonEntity):
    """Button entity to trigger a router reboot via the coordinator."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        """Initialize the reboot button."""
        super().__init__(coordinator)
        self._entry = entry
        host = getattr(coordinator.client, "host", "unknown")
        self._attr_name = f"ZTE Router {host} Reboot"
        self._attr_unique_id = f"{entry.entry_id}_reboot"
        self._attr_should_poll = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {host}",
            manufacturer="ZTE",
            model=getattr(coordinator.client, "model", "unknown"),
        )

    async def async_press(self) -> None:  # type: ignore[override]
        """Handle the button press to reboot the router."""
        host = getattr(self.coordinator.client, "host", "unknown")
        _LOGGER.info("Reboot requested via button for host: %s", host)
        try:
            success = await self.coordinator.async_reboot_router()
            if not success:
                _LOGGER.error("Router reboot failed for host: %s", host)
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.exception("Exception while rebooting router %s: %s", host, exc)