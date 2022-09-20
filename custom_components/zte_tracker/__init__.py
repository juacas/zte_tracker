"""The ZTE component."""
import logging
from datetime import datetime

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import discovery
from .zteclient.zte_client import zteClient
from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "device_tracker"]


def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    plattform_conf = config.get(DOMAIN)
    _LOGGER.debug("Client initialized with {0}:{1}@{2}".format(
        plattform_conf[CONF_USERNAME], plattform_conf[CONF_PASSWORD], plattform_conf[CONF_HOST]))

    client = zteClient(plattform_conf[CONF_HOST],
                           plattform_conf[CONF_USERNAME],
                           plattform_conf[CONF_PASSWORD])
    # Create DATA dict
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['client'] = client
    hass.data[DOMAIN]['last_reboot'] = None
    hass.data[DOMAIN]['scanning'] = False
    hass.data[DOMAIN]['statusmsg'] = 'OK'
    hass.data[DOMAIN]['status'] = 'on'

    def handle_reboot(call):
        """Handle the service call."""
        # name = call.data.get(ATTR_NAME, DEFAULT_NAME)
        result = client.reboot()
        hass.data[DOMAIN]["last_reboot"] = datetime.now()
        hass.states.set(f"{DOMAIN}.last_reboot", datetime.now())
        return True

    hass.services.register(DOMAIN, "reboot", handle_reboot)

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, platform, DOMAIN, plattform_conf, config
            )
        )

    _LOGGER.debug(f"Register {DOMAIN} service '{DOMAIN}.reboot'")
    # Return boolean to indicate that initialization was successfully.
    return True
