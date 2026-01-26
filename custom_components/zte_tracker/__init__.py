"""The ZTE component."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    DEFAULT_QUERY_ROUTER_DETAILS,
    DEFAULT_QUERY_WAN_STATUS,
    DOMAIN,
    PLATFORMS,
)
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
    # Migrate legacy config keys from entry.data to entry.options if present
    try:
        data_copy = dict(entry.data)
        options_copy = dict(entry.options) if entry.options is not None else {}
        migrated = False
        for key in (CONF_QUERY_WAN_STATUS, CONF_QUERY_ROUTER_DETAILS):
            if key in data_copy and key not in options_copy:
                options_copy[key] = data_copy.pop(key)
                migrated = True
        if migrated:
            _LOGGER.info(
                "Migrating ZTE config keys from data to options for entry %s",
                entry.entry_id,
            )
            hass.config_entries.async_update_entry(
                entry, data=data_copy, options=options_copy
            )
    except Exception as ex:  # defensive: don't block setup on migration errors
        _LOGGER.debug("Error migrating config entry options: %s", ex)

    coordinator = ZteDataCoordinator(hass, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register all services
    setup_services(hass)

    # Register an update listener to apply option changes at runtime
    async def _async_options_updated(
        hass: HomeAssistant, updated_entry: ConfigEntry
    ) -> None:
        """Handle updated options for an entry."""
        coordinator = hass.data.get(DOMAIN, {}).get(updated_entry.entry_id)
        if not coordinator:
            return

        # Resolve values with options overriding data
        query_wan = updated_entry.options.get(
            CONF_QUERY_WAN_STATUS,
            updated_entry.data.get(CONF_QUERY_WAN_STATUS, DEFAULT_QUERY_WAN_STATUS),
        )
        query_router = updated_entry.options.get(
            CONF_QUERY_ROUTER_DETAILS,
            updated_entry.data.get(
                CONF_QUERY_ROUTER_DETAILS, DEFAULT_QUERY_ROUTER_DETAILS
            ),
        )

        # Apply to existing client
        client = getattr(coordinator, "client", None)
        if client:
            client.query_wan_status = bool(query_wan)
            client.query_router_details = bool(query_router)

        # Request an immediate refresh so the new options take effect
        try:
            await coordinator.async_request_refresh()
        except Exception:
            # If refresh fails, schedule a full reload of the entry
            await async_reload_entry(hass, updated_entry)

    entry.add_update_listener(_async_options_updated)

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


REBOOT_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("host"): vol.Coerce(str),
    }
)

REMOVE_TRACKED_ENTITY_SCHEMA = vol.Schema(
    {
        vol.Required("mac"): cv.string,
    }
)

REMOVE_UNIDENTIFIED_SERVICE_SCHEMA = vol.Schema({})


async def async_reboot_service(call: ServiceCall):
    """Reboot router(s) for the specified host, or all if not specified."""
    hass = call.hass
    host = call.data.get("host")
    rebooted = []

    for entry_id, coordinator in hass.data[DOMAIN].items():
        if entry_id == "yaml_config":
            continue
        client = getattr(coordinator, "client", None)
        if not client:
            continue
        if host:
            if getattr(client, "host", None) == host:
                # Use coordinator's async method to avoid blocking the event loop
                if await coordinator.async_reboot_router():
                    rebooted.append(host)
        else:
            if await coordinator.async_reboot_router():
                rebooted.append(client.host)

    if rebooted:
        _LOGGER.info("Rebooted routers: %s", ", ".join(rebooted))
    else:
        _LOGGER.warning("No routers rebooted. Host: %s", host)
        raise HomeAssistantError(f"No routers rebooted for host: {host}")


async def async_remove_tracked_entity(call: ServiceCall):
    """Remove a tracked device entity by MAC address."""
    hass = call.hass
    mac = call.data.get("mac")
    if not mac:
        _LOGGER.error("No MAC address provided for removal.")
        return
    # Remove entity using entity registry
    entity_registry = er.async_get(hass)
    # Try all entry_ids for robustness
    removed = False
    for entry_id in hass.data.get(DOMAIN, {}):
        unique_id = f"{entry_id}_{mac.replace(':', '_')}"
        entity_id = entity_registry.async_get_entity_id(
            "device_tracker", DOMAIN, unique_id
        )
        if entity_id:
            entity_registry.async_remove(entity_id)
            _LOGGER.info("Removed tracked entity for MAC: %s", mac)
            removed = True
    if not removed:
        _LOGGER.warning("No entity found for MAC: %s", mac)
        raise HomeAssistantError(f"No entity found for MAC: {mac}")


async def async_remove_unidentified_entities_service(call: ServiceCall):
    """Service to remove all device_tracker entities for this integration that have no unique_id."""
    hass = call.hass
    entity_registry = er.async_get(hass)
    removed = 0
    for entity_id, entity in entity_registry.entities.items():
        if entity.domain == "device_tracker" and not entity.unique_id:
            entity_registry.async_remove(entity_id)
            _LOGGER.info("Removed unidentified device_tracker entity: %s", entity_id)
            removed += 1
    if removed == 0:
        _LOGGER.info("No unidentified device_tracker entities found to remove.")
    else:
        _LOGGER.info("Removed %d unidentified device_tracker entities.", removed)


def setup_services(hass):
    hass.services.async_register(
        DOMAIN,
        "reboot",
        async_reboot_service,
        schema=REBOOT_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "remove_tracked_entity",
        async_remove_tracked_entity,
        schema=REMOVE_TRACKED_ENTITY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        "remove_unidentified_entities",
        async_remove_unidentified_entities_service,
        schema=REMOVE_UNIDENTIFIED_SERVICE_SCHEMA,
    )
