"""Legacy device tracker support for ZTE routers - kept for backward compatibility."""
from __future__ import annotations

import logging
from collections import namedtuple
from typing import Any

from homeassistant.components.device_tracker import DeviceScanner
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ICONS
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)

Device = namedtuple("Device", ["name", "ip", "mac", "state", "icon"])


def get_scanner(hass: HomeAssistant, config: dict[str, Any]) -> zteDeviceScanner | None:
    """Validate the configuration and return a ZTE scanner."""
    # Check if we have modern coordinator setup
    if DOMAIN in hass.data and any(
        isinstance(v, dict) and "coordinator" in str(type(v).get("coordinator", ""))
        for v in hass.data[DOMAIN].values()
    ):
        _LOGGER.warning(
            "ZTE Tracker is using modern config entry setup. "
            "Legacy device_tracker scanner is not needed."
        )
        return None
    
    # Legacy setup fallback
    shared_data = hass.data.get(DOMAIN, {})
    scanner = shared_data.get("scanner")
    return scanner


class zteDeviceScanner(DeviceScanner):
    """Legacy device scanner for ZTE routers."""

    def __init__(self, hass: HomeAssistant, cli: zteClient) -> None:
        """Initialize the scanner."""
        _LOGGER.info(
            "Initializing legacy ZTE device scanner for model %s", cli.model
        )
        _LOGGER.info("Supported models: %s", cli.get_models())
        
        self.router_client = cli
        self.hass = hass
        self.last_results: list[Device] = []
        self.last_seen_devices: list[str] = []
        self.status = "on"
        self.statusmsg = ""
        self.scanning = True

    def pause(self) -> None:
        """Pause the scanner."""
        self.status = "paused"
        self.scanning = False
        self.statusmsg = "Tracker is paused."
        _LOGGER.info("Tracker is paused.")

    def resume(self) -> None:
        """Resume the scanner."""
        self.status = "on"
        self.scanning = True
        self.statusmsg = "Tracker is resumed."
        _LOGGER.info("Tracker is resumed.")

    def scan_devices(self) -> list[str]:
        """Scan for new devices and return a list with found device IDs."""
        _LOGGER.debug("Scan_devices invoked.")
        if not self._update_info():
            self.scanning = False
            _LOGGER.warning("Can't update device list")
            return []
        
        clients = [client.mac for client in self.last_results]
        self.last_seen_devices = clients
        self.scanning = True
        return clients

    def get_device_name(self, device: str) -> str | None:
        """Return the name of the given device or None if we don't know."""
        if not self.last_results:
            return None
        for client in self.last_results:
            if client.mac == device:
                return client.name
        return None

    def _update_info(self) -> bool:
        """Ensure the information from the router is up to date."""
        data = self._get_data()
        if not data:
            return False
        
        # Filter out clients that are not connected
        active_clients = [client for client in data if client.state]
        self.last_results = active_clients

        _LOGGER.debug(
            "%d Active clients: %s",
            len(active_clients),
            ", ".join(f"{client.mac} {client.name}" for client in active_clients),
        )
        return True

    def _get_data(self) -> list[Device]:
        """Get the devices' data from the router."""
        devices = []
        try:
            if self.status == "paused":
                _LOGGER.info("Tracker is paused. Scan bypassed.")
                self.scanning = False
                return []
            
            if not self.router_client.login():
                self.scanning = False
                _LOGGER.warning(
                    "Login failed: %s@%s",
                    self.router_client.username,
                    self.router_client.host,
                )
                return []
            
            device_list = self.router_client.get_devices_response()
        except Exception as ex:
            _LOGGER.error("Error getting device data: %s", ex)
            return []
        finally:
            try:
                self.router_client.logout()
            except Exception:
                pass

        self.statusmsg = self.router_client.statusmsg
        self.scanning = True

        # Create a list of Device tuples
        if device_list:
            for device in device_list:
                icon = ICONS.get(device.get("IconType"))
                dev = Device(
                    device.get("HostName", "Unknown"),
                    device.get("IPAddress", ""),
                    device.get("MACAddress", ""),
                    device.get("Active", False),
                    icon,
                )
                devices.append(dev)
        
        return devices