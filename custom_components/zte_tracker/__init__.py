"""The ZTE component."""
import logging
from datetime import datetime
from .device_tracker import zteDeviceScanner

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_MODEL
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .zteclient.zte_client import zteClient
from .const import DOMAIN, PLATFORMS

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_MODEL): vol.In(zteClient.get_models(None)),
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    plattform_conf = config.get(DOMAIN)
    _LOGGER.debug("Client initialized for ZTE {0} @{1}".format(plattform_conf[CONF_MODEL]
        , plattform_conf[CONF_HOST]))

    client = zteClient(plattform_conf[CONF_HOST],
                           plattform_conf[CONF_USERNAME],
                           plattform_conf[CONF_PASSWORD],
                           plattform_conf[CONF_MODEL])
    scanner = zteDeviceScanner(hass, client)

    # Create DATA dict
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['scanner'] = scanner
    hass.data[DOMAIN]['client'] = client
    hass.data[DOMAIN]['last_reboot'] = None

    def handle_reboot(call):
        """Handle the service call."""
        # name = call.data.get(ATTR_NAME, DEFAULT_NAME)
        result = client.reboot()
        hass.data[DOMAIN]["last_reboot"] = datetime.now()
        hass.states.set(f"{DOMAIN}.last_reboot", datetime.now())
        return True
    def handle_pause(call):
        """Handle the service call."""
        _LOGGER.debug("Pause service called")
        if scanner.status == 'on':
            scanner.pause()
        else:
            scanner.resume()
        return True

    hass.services.register(DOMAIN, "reboot", handle_reboot)
    _LOGGER.debug(f"Register {DOMAIN} service '{DOMAIN}.reboot'")
    hass.services.register(DOMAIN, "pause", handle_pause)
    _LOGGER.debug(f"Register {DOMAIN} service '{DOMAIN}.pause'")


    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, platform, DOMAIN, plattform_conf, config
            )
        )
    # Return boolean to indicate that initialization was successfully.
    return True
