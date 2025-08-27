"""The ZTE component."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import ZteDataCoordinator
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)

# Configuration schema for YAML setup (legacy support)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_MODEL): vol.In(zteClient.get_models()),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the ZTE component from YAML configuration."""
    hass.data.setdefault(DOMAIN, {})
    
    # Legacy YAML configuration support
    if DOMAIN in config:
        _LOGGER.warning(
            "YAML configuration for ZTE Tracker is deprecated. "
            "Please configure through the UI instead."
        )
        # Store for migration purposes
        hass.data[DOMAIN]["yaml_config"] = config[DOMAIN]
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ZTE Tracker from a config entry."""
    coordinator = ZteDataCoordinator(hass, entry)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_handle_reboot(call: ServiceCall) -> None:
        """Handle the reboot service call."""
        success = await coordinator.async_reboot_router()
        if success:
            hass.states.async_set(f"{DOMAIN}.last_reboot", datetime.now())
            _LOGGER.info("Router reboot initiated successfully")
        else:
            _LOGGER.error("Failed to initiate router reboot")

    async def async_handle_pause(call: ServiceCall) -> None:
        """Handle the pause/resume service call."""
        if coordinator.paused:
            coordinator.resume_scanning()
        else:
            coordinator.pause_scanning()

    # Register services only if not already registered
    if not hass.services.has_service(DOMAIN, "reboot"):
        hass.services.async_register(DOMAIN, "reboot", async_handle_reboot)
        _LOGGER.debug("Registered service: %s.reboot", DOMAIN)

    if not hass.services.has_service(DOMAIN, "pause"):
        hass.services.async_register(DOMAIN, "pause", async_handle_pause)
        _LOGGER.debug("Registered service: %s.pause", DOMAIN)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
