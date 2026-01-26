"""Config flow for ZTE Tracker integration."""

from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_QUERY_ROUTER_DETAILS,
    DEFAULT_QUERY_WAN_STATUS,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)


def validate_host(host: str) -> str:
    """Validate host address."""
    host = host.strip()

    # Check if it's a valid IP address
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass

    # Check if it's a valid hostname/FQDN
    hostname_pattern = re.compile(r"^(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    if "." in host:
        # FQDN validation
        if all(hostname_pattern.match(part) for part in host.split(".")):
            return host
    elif hostname_pattern.match(host):
        # Simple hostname
        return host

    raise vol.Invalid("Invalid host address")


def validate_username(username: str) -> str:
    """Validate username."""
    username = username.strip()
    if not username:
        raise vol.Invalid("Username cannot be empty")
    if len(username) > 64:
        raise vol.Invalid("Username too long")
    # Basic alphanumeric + common characters
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        raise vol.Invalid("Username contains invalid characters")
    return username


def validate_password(password: str) -> str:
    """Validate password."""
    if not password:
        raise vol.Invalid("Password cannot be empty")
    if len(password) > 128:
        raise vol.Invalid("Password too long")
    return password


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): cv.string,
        vol.Required(CONF_MODEL, default="F6640"): vol.In(zteClient.get_models()),
        vol.Required(
            CONF_QUERY_WAN_STATUS, default=DEFAULT_QUERY_WAN_STATUS
        ): cv.boolean,
        vol.Required(
            CONF_QUERY_ROUTER_DETAILS, default=DEFAULT_QUERY_ROUTER_DETAILS
        ): cv.boolean,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Additional validation
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    model = data[CONF_MODEL]
    query_router_details = data[CONF_QUERY_ROUTER_DETAILS]
    query_wan_status = data[CONF_QUERY_WAN_STATUS]

    # Validate model is supported
    if model not in zteClient.get_models():
        raise ValueError(f"Unsupported model: {model}")

    client = zteClient(
        host, username, password, model, query_wan_status, query_router_details
    )

    # Test the connection in a separate thread to avoid blocking
    def test_connection():
        try:
            success = client.login()
            statusmsg = client.statusmsg or "Unknown error"
            if success:
                # Verify we can actually get data
                devices = client.get_devices_response()
                if devices is not None:
                    return (True, statusmsg)
                else:
                    return (False, "Connected but could not retrieve device data.")
            else:
                return (False, statusmsg)
        except Exception as ex:
            _LOGGER.error("Connection test failed: %s", ex)
            return (False, str(ex))
        finally:
            try:
                client.logout()
            except Exception:
                pass

    # Run connection test in executor to avoid blocking
    result, statusmsg = await hass.async_add_executor_job(test_connection)

    if not result:
        raise ConnectionError(statusmsg)

    # Return info that you want to store in the config entry
    return {"title": f"ZTE Router {model} ({host})", "statusmsg": statusmsg}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZTE Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validación personalizada antes de llamar a validate_input
            try:
                user_input[CONF_HOST] = validate_host(user_input[CONF_HOST])
            except vol.Invalid as ex:
                errors[CONF_HOST] = "invalid_host"
            try:
                user_input[CONF_USERNAME] = validate_username(user_input[CONF_USERNAME])
            except vol.Invalid as ex:
                errors[CONF_USERNAME] = "invalid_username"
            try:
                user_input[CONF_PASSWORD] = validate_password(user_input[CONF_PASSWORD])
            except vol.Invalid as ex:
                errors[CONF_PASSWORD] = "invalid_password"
            if not errors:
                try:
                    info = await validate_input(self.hass, user_input)
                except ConnectionError as ex:
                    errors["base"] = str(ex)
                    # Optionally, add statusmsg to errors for display in UI if supported
                    errors["statusmsg"] = str(ex)
                except ValueError as ex:
                    errors["base"] = "invalid_model"
                    _LOGGER.error("Invalid model: %s", ex)
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    # Check if already configured
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()
                    # Optionally, add statusmsg to entry data for diagnostics
                    user_input["statusmsg"] = info.get("statusmsg", "")
                    return self.async_create_entry(title=info["title"], data=user_input)

        defaults = user_input or {}
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=defaults.get(CONF_HOST, DEFAULT_HOST)
                ): cv.string,
                vol.Required(
                    CONF_USERNAME, default=defaults.get(CONF_USERNAME, DEFAULT_USERNAME)
                ): cv.string,
                vol.Required(
                    CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, DEFAULT_PASSWORD)
                ): cv.string,
                vol.Required(
                    CONF_MODEL, default=defaults.get(CONF_MODEL, "F6640")
                ): vol.In(zteClient.get_models()),
                vol.Required(
                    CONF_QUERY_WAN_STATUS,
                    default=defaults.get(
                        CONF_QUERY_WAN_STATUS, DEFAULT_QUERY_WAN_STATUS
                    ),
                ): cv.boolean,
                vol.Required(
                    CONF_QUERY_ROUTER_DETAILS,
                    default=defaults.get(
                        CONF_QUERY_ROUTER_DETAILS, DEFAULT_QUERY_ROUTER_DETAILS
                    ),
                ): cv.boolean,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def __init__(self, config_entry) -> None:
        # Avoid using attribute name `config_entry` which is deprecated.
        # Store the entry under a private name to be compatible with newer HA versions.
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Defaults come from options, then stored data, then module defaults
        current_wan = self._config_entry.options.get(
            CONF_QUERY_WAN_STATUS,
            self._config_entry.data.get(
                CONF_QUERY_WAN_STATUS, DEFAULT_QUERY_WAN_STATUS
            ),
        )
        current_router = self._config_entry.options.get(
            CONF_QUERY_ROUTER_DETAILS,
            self._config_entry.data.get(
                CONF_QUERY_ROUTER_DETAILS, DEFAULT_QUERY_ROUTER_DETAILS
            ),
        )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_QUERY_WAN_STATUS, default=current_wan): cv.boolean,
                vol.Required(
                    CONF_QUERY_ROUTER_DETAILS, default=current_router
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
