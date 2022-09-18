"""Support for ZTE routers."""
from .const import DOMAIN, DOMAIN_DATA, ICONS
import voluptuous as vol
import logging
from collections import namedtuple

from homeassistant.components.device_tracker import (
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import config_validation as cv, entity_platform, service
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)


def get_scanner(hass, config):
    """Validate the configuration and return a ZTE scanner."""
    shared_data = hass.data[DOMAIN]
    client = shared_data.get('client')
    scanner = zteDeviceScanner(hass, client)
    return scanner


Device = namedtuple("Device", ["name", "ip", "mac", "state", "icon"])


class zteDeviceScanner(DeviceScanner):
    """This class queries a router running ZTE firmware."""

    def __init__(self, hass, cli):
        """Initialize the scanner.
        :type cli: zteClient
        """
        _LOGGER.info("===========================")
        _LOGGER.info(" ZTE start device Scanner ")
        _LOGGER.info("===========================")
        self.router_client = cli
        self.hass = hass
        self.last_results = []

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        _LOGGER.debug("Scan_devices invoked.")
        if self._update_info() == False:
            # self.hass.data[DOMAIN]['devices'] = None
            self.hass.data[DOMAIN]['scanning'] = False
            _LOGGER.warning("Can't update device list")
            return []
        else:
            clients = [client.mac for client in self.last_results]
            self.hass.data[DOMAIN]['devices'] = clients
            self.hass.data[DOMAIN]['scanning'] = True
            return clients

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        if not self.last_results:
            return None
        for client in self.last_results:
            if client.mac == device:
                return client.name
        return None

    def _update_info(self):
        """Ensure the information from the router is up to date.

        Return boolean if scanning successful.
        """
        data = self._get_data()
        if not data:
            return False

        active_clients = [client for client in data if client.state]
        self.last_results = active_clients

        _LOGGER.debug(
            "%s Active clients: %s",
            len(active_clients),
            ",".join(f"{client.mac} {client.name}" for client in active_clients),
        )
        return True

    def _get_data(self):
        """Get the devices' data from the router.

        Returns a list with all the devices known to the router DHCP server.
        """
        devices = []
        try:
            if not self.router_client.login():
                self.hass.states.set(f"{DOMAIN}.statusmsg", self.router_client.statusmsg)
                _LOGGER.warning("Login failed: {0}:{1}@{2}".format(self.router_client.username, self.router_client.password,self.router_client.host))
                self.router_client.logout()
                return devices

            devices_json = self.router_client.get_devices_response()
        finally:
            self.router_client.logout()

        self.hass.states.set(f"{DOMAIN}.scanning", devices_json != False)

        if devices_json != False:
            for device in devices_json:
                # _LOGGER.debug("Device: {0}".format(device))
                icon = ICONS.get(device['IconType'], None)
                dev = Device(
                    device.get('HostName', 'Unknown'),
                    device['IPAddress'],
                    device['MACAddress'],
                    device['Active'],
                    icon
                )
                #               _LOGGER.debug("Device: {0}".format(dev))
                devices.append(dev)
            return devices
        else:
            return []
