"""Config flow for ZTE Tracker integration."""
from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_USERNAME, DEFAULT_PASSWORD
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
    hostname_pattern = re.compile(
        r'^(?!-)[A-Z\d-]{1,63}(?<!-)$', re.IGNORECASE
    )
    if '.' in host:
        # FQDN validation
        if all(hostname_pattern.match(part) for part in host.split('.')):
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
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
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
        vol.Required(CONF_HOST, default=DEFAULT_HOST): validate_host,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): validate_username,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): validate_password,
        vol.Required(CONF_MODEL, default="F6640"): vol.In(zteClient.get_models()),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Additional validation
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    model = data[CONF_MODEL]
    
    # Validate model is supported
    if model not in zteClient.get_models():
        raise ValueError(f"Unsupported model: {model}")
    
    client = zteClient(host, username, password, model)

    # Test the connection in a separate thread to avoid blocking
    def test_connection():
        try:
            success = client.login()
            if success:
                # Verify we can actually get data
                devices = client.get_devices_response()
                return devices is not None
            return False
        except Exception as ex:
            _LOGGER.error("Connection test failed: %s", ex)
            return False
        finally:
            try:
                client.logout()
            except Exception:
                pass

    # Run connection test in executor to avoid blocking
    result = await hass.async_add_executor_job(test_connection)
    
    if not result:
        raise ConnectionError("Cannot connect to router or retrieve device data")

    # Return info that you want to store in the config entry
    return {"title": f"ZTE Router {model} ({host})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZTE Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except vol.Invalid as ex:
                errors["base"] = "invalid_input"
                _LOGGER.error("Invalid input: %s", ex)
            except ConnectionError:
                errors["base"] = "cannot_connect"
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
                
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )