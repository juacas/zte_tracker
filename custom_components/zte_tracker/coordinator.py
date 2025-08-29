"""Data coordinator for ZTE Tracker integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)
FAST_UPDATE_INTERVAL = timedelta(seconds=30)
SLOW_UPDATE_INTERVAL = timedelta(seconds=120)


class ZteDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ZTE router data with intelligent caching."""

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
        self._last_device_count = 0
        self._stable_count = 0
        self._device_cache: dict[str, dict[str, Any]] = {}
        self._last_successful_update: datetime | None = None

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

    def _adjust_update_interval(self, device_count: int) -> None:
        """Adjust update interval based on device activity."""
        if device_count == self._last_device_count:
            self._stable_count += 1
        else:
            self._stable_count = 0
            self._last_device_count = device_count

        # If devices are stable for a while, slow down polling
        if self._stable_count > 5:
            new_interval = SLOW_UPDATE_INTERVAL
        elif self._stable_count < 2:
            new_interval = FAST_UPDATE_INTERVAL
        else:
            new_interval = DEFAULT_UPDATE_INTERVAL

        if self.update_interval != new_interval:
            _LOGGER.debug(
                "Adjusting update interval from %s to %s (stable count: %d)",
                self.update_interval,
                new_interval,
                self._stable_count,
            )
            self.update_interval = new_interval

    async def async_reboot_router(self) -> bool:
        """Reboot the router."""
        def _reboot():
            try:
                return self.client.reboot()
            except Exception as ex:
                _LOGGER.error("Failed to reboot router: %s", ex)
                return False

        return await self.hass.async_add_executor_job(_reboot)

    def _merge_device_data(self, new_devices: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge new device data with cached data for better stability."""
        processed_devices = {}

        # Update cache with new data
        current_macs = set()
        for device in new_devices:
            mac = device.get("MACAddress")
            if not mac:
                continue

            current_macs.add(mac)
            device_data = {
                "name": device.get("HostName", "Unknown"),
                "ip": device.get("IPAddress", ""),
                "mac": mac,
                "active": device.get("Active", False),
                "icon_type": device.get("IconType"),
                "network_type": device.get("NetworkType", "Unknown"),
                "last_seen": datetime.now().isoformat(),
                "port": device.get("Port", ""),  # LAN port or WLAN ESSID
                "LinkTime": device.get("LinkTime", ""),
                "ConnectTime": device.get("ConnectTime", ""),
            }

            # Merge with cached data if available
            if mac in self._device_cache:
                cached = self._device_cache[mac]
                # Keep the name if new one is generic and cached one is better
                if device_data["name"] in ("Unknown", mac) and cached.get("name", "Unknown") not in ("Unknown", mac):
                    device_data["name"] = cached["name"]

                # Keep last_seen from cache if device is not currently active
                if not device_data["active"] and cached.get("last_seen"):
                    device_data["last_seen"] = cached["last_seen"]

            self._device_cache[mac] = device_data
            processed_devices[mac] = device_data

        # Mark devices not seen in this scan as inactive but keep in cache
        for mac, cached_device in self._device_cache.items():
            if mac not in current_macs:
                # Keep device in processed list but mark as inactive
                inactive_device = cached_device.copy()
                inactive_device["active"] = False
                processed_devices[mac] = inactive_device

        return processed_devices

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the router."""
        if self._paused:
            _LOGGER.debug("Scanning paused, returning cached data")
            # Return cached data when paused
            return {
                "devices": {mac: data.copy() for mac, data in self._device_cache.items()},
                "router_info": {
                    "host": self.client.host,
                    "model": self.client.model,
                    "status": "paused",
                },
            }

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
            # Return cached data on failure if we have it and it's recent
            if (self._device_cache and self._last_successful_update and
                datetime.now() - self._last_successful_update < timedelta(minutes=10)):
                _LOGGER.warning("Using cached data due to connection failure")
                return {
                    "devices": {mac: data.copy() for mac, data in self._device_cache.items()},
                    "router_info": {
                        "host": self.client.host,
                        "model": self.client.model,
                        "status": "unavailable",
                    },
                }
            raise UpdateFailed("Failed to communicate with router")

        self._available = True
        self._last_successful_update = datetime.now()

        # Process devices with caching
        processed_devices = self._merge_device_data(devices)

        # Adjust polling interval based on device activity
        active_count = len([d for d in processed_devices.values() if d.get("active")])
        self._adjust_update_interval(active_count)

        return {
            "devices": processed_devices,
            "router_info": {
                "host": self.client.host,
                "model": self.client.model,
                "status": "connected",
                "last_update": self._last_successful_update.isoformat(),
                "active_devices": active_count,
                "total_devices": len(processed_devices),
            }
        }