"""Tests for the setup and options flows."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker.config_flow import (
    ConfigFlow,
    OptionsFlowHandler,
    validate_host,
    validate_input,
    validate_password,
    validate_username,
)
from custom_components.zte_tracker.const import (
    CONF_MESH_TOPOLOGY,
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    CONF_SESSION_REUSE,
    DEFAULT_QUERY_ROUTER_DETAILS,
    DEFAULT_QUERY_WAN_STATUS,
    DEFAULT_SESSION_REUSE,
    DOMAIN,
)

USER_INPUT = {
    CONF_HOST: "192.168.1.1",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "secret",
    CONF_MODEL: "F6640",
    CONF_QUERY_WAN_STATUS: True,
    CONF_QUERY_ROUTER_DETAILS: True,
    CONF_SESSION_REUSE: False,
}


def _config_flow(hass) -> ConfigFlow:
    flow = ConfigFlow()
    flow.hass = hass
    return flow


def _options_entry(**kwargs) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry-1",
        title="ZTE Router",
        data={
            CONF_HOST: "192.168.1.1",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            CONF_MODEL: "F6640",
            CONF_QUERY_WAN_STATUS: DEFAULT_QUERY_WAN_STATUS,
            CONF_QUERY_ROUTER_DETAILS: DEFAULT_QUERY_ROUTER_DETAILS,
            CONF_SESSION_REUSE: DEFAULT_SESSION_REUSE,
            **kwargs.pop("data", {}),
        },
        options={
            CONF_QUERY_WAN_STATUS: True,
            CONF_QUERY_ROUTER_DETAILS: True,
            CONF_SESSION_REUSE: False,
            CONF_MESH_TOPOLOGY: False,
            **kwargs.pop("options", {}),
        },
        unique_id="192.168.1.1",
        **kwargs,
    )


@pytest.mark.parametrize("host", ["192.168.1.1", "router", "router.example.net"])
def test_validate_host_accepts_supported_formats(host: str) -> None:
    """Accepted host formats should pass untouched."""
    assert validate_host(host) == host


@pytest.mark.parametrize("host", ["bad host", "-router", "router.", ""])
def test_validate_host_rejects_bad_formats(host: str) -> None:
    """Invalid host formats should fail early."""
    with pytest.raises(vol.Invalid):
        validate_host(host)


def test_validate_username_and_password_enforce_basic_rules() -> None:
    """Invalid credentials should be rejected before any router call."""
    assert validate_username(" user.name-1 ") == "user.name-1"
    assert validate_password("secret") == "secret"

    with pytest.raises(vol.Invalid):
        validate_username("")
    with pytest.raises(vol.Invalid):
        validate_username("bad user")
    with pytest.raises(vol.Invalid):
        validate_password("")


@pytest.mark.asyncio
async def test_validate_input_returns_title_after_successful_probe() -> None:
    """A working probe should yield the config-entry title."""
    client = SimpleNamespace(
        login=Mock(return_value=True),
        get_devices_response=Mock(return_value=[{"MACAddress": "AA:BB"}]),
        logout=Mock(),
        statusmsg="ready",
    )
    client_factory = Mock(return_value=client)
    client_factory.get_models.return_value = ["F6640", "H288A"]
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args))
    )

    with patch("custom_components.zte_tracker.config_flow.zteClient", client_factory):
        result = await validate_input(hass, dict(USER_INPUT))

    assert result == {"title": "ZTE Router F6640 (192.168.1.1)", "statusmsg": "ready"}
    client_factory.assert_called_once_with(
        "192.168.1.1",
        "admin",
        "secret",
        "F6640",
        query_wan_status=True,
        query_router_details=True,
    )
    client.logout.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_raises_connection_error_for_failed_probe() -> None:
    """A failed login should surface the router error."""
    client = SimpleNamespace(
        login=Mock(return_value=False),
        get_devices_response=Mock(return_value=[]),
        logout=Mock(),
        statusmsg="bad credentials",
    )
    client_factory = Mock(return_value=client)
    client_factory.get_models.return_value = ["F6640"]
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args))
    )

    with patch("custom_components.zte_tracker.config_flow.zteClient", client_factory):
        with pytest.raises(ConnectionError, match="bad credentials"):
            await validate_input(hass, dict(USER_INPUT))

    client.logout.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_rejects_unsupported_models() -> None:
    """A model outside the allowlist should never instantiate the client."""
    client_factory = Mock()
    client_factory.get_models.return_value = ["H288A"]
    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args))
    )

    with patch("custom_components.zte_tracker.config_flow.zteClient", client_factory):
        with pytest.raises(ValueError, match="Unsupported model"):
            await validate_input(hass, dict(USER_INPUT))

    client_factory.assert_not_called()


@pytest.mark.asyncio
async def test_async_step_user_shows_form_before_submission(mock_hass) -> None:
    """The initial user step should render the setup form."""
    result = await _config_flow(mock_hass).async_step_user()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_async_step_user_reports_field_validation_errors(mock_hass) -> None:
    """Field validation should stop bad data before router I/O."""
    flow = _config_flow(mock_hass)

    result = await flow.async_step_user(
        {
            **USER_INPUT,
            CONF_HOST: "bad host",
            CONF_USERNAME: "bad user",
            CONF_PASSWORD: "",
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_HOST: "invalid_host",
        CONF_USERNAME: "invalid_username",
        CONF_PASSWORD: "invalid_password",
    }


@pytest.mark.asyncio
async def test_async_step_user_creates_entry_on_success(mock_hass) -> None:
    """A successful probe should create the entry with submitted data."""
    flow = _config_flow(mock_hass)

    with (
        patch(
            "custom_components.zte_tracker.config_flow.validate_input",
            AsyncMock(return_value={"title": "ZTE Router F6640 (192.168.1.1)"}),
        ),
        patch.object(flow, "async_set_unique_id", AsyncMock()) as set_unique_id,
        patch.object(flow, "_abort_if_unique_id_configured") as abort_if_configured,
    ):
        result = await flow.async_step_user(dict(USER_INPUT))

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZTE Router F6640 (192.168.1.1)"
    assert result["data"] == USER_INPUT
    set_unique_id.assert_awaited_once_with("192.168.1.1")
    abort_if_configured.assert_called_once()


@pytest.mark.asyncio
async def test_async_step_user_reports_connection_errors(mock_hass) -> None:
    """Connection failures should be reflected back into the form."""
    flow = _config_flow(mock_hass)

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input",
        AsyncMock(side_effect=ConnectionError("bad credentials")),
    ):
        result = await flow.async_step_user(dict(USER_INPUT))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "bad credentials"
    assert result["errors"]["statusmsg"] == "bad credentials"


@pytest.mark.asyncio
async def test_async_step_user_handles_invalid_model_errors(mock_hass) -> None:
    """Validation ValueErrors should map to the invalid model error key."""
    flow = _config_flow(mock_hass)

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input",
        AsyncMock(side_effect=ValueError("Unsupported model: F6640")),
    ):
        result = await flow.async_step_user(dict(USER_INPUT))

    assert result["errors"]["base"] == "invalid_model"


@pytest.mark.asyncio
async def test_async_step_user_reraises_duplicate_abort(mock_hass) -> None:
    """Duplicate hosts should stop the flow as already configured."""
    flow = _config_flow(mock_hass)

    with (
        patch(
            "custom_components.zte_tracker.config_flow.validate_input",
            AsyncMock(return_value={"title": "ZTE Router F6640 (192.168.1.1)"}),
        ),
        patch.object(flow, "async_set_unique_id", AsyncMock()),
        patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=AbortFlow("already_configured"),
        ),
    ):
        with pytest.raises(AbortFlow, match="already_configured"):
            await flow.async_step_user(dict(USER_INPUT))


@pytest.mark.asyncio
async def test_async_step_user_handles_unknown_errors(mock_hass) -> None:
    """Unexpected probe failures should not crash the flow."""
    flow = _config_flow(mock_hass)

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await flow.async_step_user(dict(USER_INPUT))

    assert result["errors"]["base"] == "unknown"


def test_async_get_options_flow_returns_handler() -> None:
    """The config flow should expose its options handler."""
    entry = _options_entry()

    handler = ConfigFlow.async_get_options_flow(entry)

    assert isinstance(handler, OptionsFlowHandler)


@pytest.mark.asyncio
async def test_options_flow_shows_current_values(mock_hass) -> None:
    """The options form should start from the current entry state."""
    entry = _options_entry()
    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    result = await handler.async_step_init()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_options_flow_updates_booleans_without_revalidating(mock_hass) -> None:
    """Pure option changes should not hit the router."""
    entry = _options_entry()
    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass
    mock_hass.config_entries.async_update_entry = Mock()
    mock_hass.config_entries.async_schedule_reload = Mock()

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input", AsyncMock()
    ) as validate_input_mock:
        result = await handler.async_step_init(
            {
                CONF_HOST: "192.168.1.1",
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "secret",
                CONF_QUERY_WAN_STATUS: False,
                CONF_QUERY_ROUTER_DETAILS: False,
                CONF_SESSION_REUSE: True,
                CONF_MESH_TOPOLOGY: True,
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_QUERY_WAN_STATUS: False,
        CONF_QUERY_ROUTER_DETAILS: False,
        CONF_SESSION_REUSE: True,
        CONF_MESH_TOPOLOGY: True,
    }
    validate_input_mock.assert_not_awaited()
    mock_hass.config_entries.async_update_entry.assert_not_called()
    mock_hass.config_entries.async_schedule_reload.assert_not_called()


@pytest.mark.asyncio
async def test_options_flow_updates_credentials_and_schedules_reload(
    mock_hass,
) -> None:
    """Credential changes should be validated, persisted, and reloaded."""
    entry = _options_entry()
    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass
    mock_hass.config_entries.async_update_entry = Mock()
    mock_hass.config_entries.async_schedule_reload = Mock()

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input",
        AsyncMock(return_value={"title": "ignored"}),
    ) as validate_input_mock:
        result = await handler.async_step_init(
            {
                CONF_HOST: "router.example.net",
                CONF_USERNAME: "new-admin",
                CONF_PASSWORD: "new-secret",
                CONF_QUERY_WAN_STATUS: True,
                CONF_QUERY_ROUTER_DETAILS: False,
                CONF_SESSION_REUSE: True,
                CONF_MESH_TOPOLOGY: True,
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_QUERY_WAN_STATUS: True,
        CONF_QUERY_ROUTER_DETAILS: False,
        CONF_SESSION_REUSE: True,
        CONF_MESH_TOPOLOGY: True,
    }
    validate_input_mock.assert_awaited_once_with(
        mock_hass,
        {
            CONF_HOST: "router.example.net",
            CONF_USERNAME: "new-admin",
            CONF_PASSWORD: "new-secret",
            CONF_MODEL: "F6640",
            CONF_QUERY_WAN_STATUS: True,
            CONF_QUERY_ROUTER_DETAILS: False,
        },
    )
    mock_hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        data={
            **entry.data,
            CONF_HOST: "router.example.net",
            CONF_USERNAME: "new-admin",
            CONF_PASSWORD: "new-secret",
        },
    )
    mock_hass.config_entries.async_schedule_reload.assert_called_once_with("entry-1")


@pytest.mark.asyncio
async def test_options_flow_reports_connection_errors(mock_hass) -> None:
    """Credential validation failures should stay on the form."""
    entry = _options_entry()
    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    with patch(
        "custom_components.zte_tracker.config_flow.validate_input",
        AsyncMock(side_effect=ConnectionError("bad credentials")),
    ):
        result = await handler.async_step_init(
            {
                CONF_HOST: "router.example.net",
                CONF_USERNAME: "new-admin",
                CONF_PASSWORD: "new-secret",
                CONF_QUERY_WAN_STATUS: True,
                CONF_QUERY_ROUTER_DETAILS: True,
                CONF_SESSION_REUSE: False,
                CONF_MESH_TOPOLOGY: False,
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_options_flow_keeps_submitted_values_on_validation_error(
    mock_hass,
) -> None:
    """Submitted values should remain in the form after validation errors."""
    entry = _options_entry()
    handler = OptionsFlowHandler(entry)
    handler.hass = mock_hass

    result = await handler.async_step_init(
        {
            CONF_HOST: "bad host",
            CONF_USERNAME: "bad user",
            CONF_PASSWORD: "",
            CONF_QUERY_WAN_STATUS: False,
            CONF_QUERY_ROUTER_DETAILS: True,
            CONF_SESSION_REUSE: True,
            CONF_MESH_TOPOLOGY: False,
        }
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_HOST: "invalid_host",
        CONF_USERNAME: "invalid_username",
        CONF_PASSWORD: "invalid_password",
    }
