"""Sensor platform for zte."""
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from .const import DOMAIN, ICON
import logging
# SCAN_INTERVAL = timedelta(seconds=10)
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, _config, async_add_entities, discovery_info=None):
    """Setup sensor platform."""
    _LOGGER.debug("Adding zte entity")
    async_add_entities([zteSensor(hass, discovery_info)])


class zteSensor(Entity):
    """ zte Sensor class."""

    def __init__(self, hass, config):
        _LOGGER.debug(f"Initializing zteSensor entity: sensor.{__name__}")
        self.hass = hass
        self._attr = {}
        self._state = None
        self._unique_id = f"{DOMAIN}_sensor_main"
        self._name = DOMAIN
        self.scanner = self.hass.data[DOMAIN].get("scanner")

    async def async_update(self):
        """Update the sensor."""

        # Check the data and update the value.
        self._state = self.scanner.status
        # Format list of devices.
        devices = []
        for device in self.scanner.last_results:
            devices.append("{1} ({2}) - {3} - {0}".format(device.get("HostName"), device.get("MacAddress"), device.get("IPAddress"), device.get("State")))
        # Set/update attributes
        self._attr = {
            'last_reboot': self.hass.data[DOMAIN].get("last_reboot", None),
            'scanning': self.scanner.scanning,
            'devices': devices,
            'num_devices': len(self.scanner.last_results),
            'statusmsg': self.scanner.statusmsg
        }

    @property
    def should_poll(self):
        """Return the name of the sensor."""
        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attr
