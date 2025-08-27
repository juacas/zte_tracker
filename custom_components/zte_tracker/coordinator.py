"""Data coordinator for ZTE Tracker integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)


class ZteDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ZTE router data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = zteClient(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_MODEL],
        )
        self._available = True
        self._paused = False
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

    @property
    def available(self) -> bool:
        """Return if the router is available."""
        return self._available

    @property
    def paused(self) -> bool:
        """Return if scanning is paused."""
        return self._paused

    def pause_scanning(self) -> None:
        """Pause device scanning."""
        self._paused = True
        _LOGGER.info("ZTE tracker scanning paused")

    def resume_scanning(self) -> None:
        """Resume device scanning."""
        self._paused = False
        _LOGGER.info("ZTE tracker scanning resumed")

    async def async_reboot_router(self) -> bool:
        """Reboot the router."""
        def _reboot():
            try:
                return self.client.reboot()
            except Exception as ex:
                _LOGGER.error("Failed to reboot router: %s", ex)
                return False

        return await self.hass.async_add_executor_job(_reboot)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the router."""
        if self._paused:
            _LOGGER.debug("Scanning paused, skipping update")
            return self.data or {}

        def _fetch_devices():
            """Fetch devices in executor."""
            try:
                if not self.client.login():
                    _LOGGER.warning("Login failed: %s@%s", 
                                   self.client.username, self.client.host)
                    return None

                devices = self.client.get_devices_response()
                return devices
            except Exception as ex:
                _LOGGER.error("Error fetching device data: %s", ex)
                return None
            finally:
                try:
                    self.client.logout()
                except Exception:
                    pass

        devices = await self.hass.async_add_executor_job(_fetch_devices)
        
        if devices is None:
            self._available = False
            raise UpdateFailed("Failed to communicate with router")

        self._available = True
        
        # Process devices into a consistent format
        processed_devices = {}
        for device in devices:
            mac = device.get("MACAddress")
            if mac:
                processed_devices[mac] = {
                    "name": device.get("HostName", "Unknown"),
                    "ip": device.get("IPAddress", ""),
                    "mac": mac,
                    "active": device.get("Active", False),
                    "icon_type": device.get("IconType"),
                    "network_type": device.get("NetworkType", "Unknown"),
                }

        return {
            "devices": processed_devices,
            "router_info": {
                "host": self.client.host,
                "model": self.client.model,
                "status": "connected" if self._available else "disconnected",
            }
        }