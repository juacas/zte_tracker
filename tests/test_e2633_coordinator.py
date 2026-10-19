"""Coordinator-level tests for the ZTE E2633, with a REAL zteClient and a local fake router.

The client-level tests share their assumptions with the fake router (both written from
the same measurements). These go one level up: they drive ZteDataCoordinator through
whole poll cycles and check what a tracked device would see: a failed read must not flip
devices to "away", an expired session must lead to a new login, and the client must
recover after the network (or the router) was gone.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import _fake_e2633 as fake
import pytest
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_tracker.const import (
    CONF_MESH_TOPOLOGY,
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    CONF_SESSION_REUSE,
    DOMAIN,
)
from custom_components.zte_tracker.coordinator import ZteDataCoordinator
from custom_components.zte_tracker.zteclient.zte_client import zteClient

MAC_A = "02:00:00:00:00:01"
MAC_B = "02:00:00:00:00:02"


def _coordinator(mock_hass, router, *, session_reuse: bool) -> ZteDataCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="entry-1",
        data={
            CONF_HOST: router.host,
            CONF_USERNAME: fake.USERNAME,
            CONF_PASSWORD: fake.PASSWORD,
            CONF_MODEL: "E2633",
        },
        options={
            CONF_QUERY_WAN_STATUS: True,
            CONF_QUERY_ROUTER_DETAILS: True,
            CONF_SESSION_REUSE: session_reuse,
            CONF_MESH_TOPOLOGY: False,
        },
    )
    # Run the blocking client calls inline (no executor), as test_coordinator_runtime does.
    mock_hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    # The fake router speaks plain HTTP; the E2633 default scheme is https.
    with patch(
        "custom_components.zte_tracker.coordinator.zteClient",
        side_effect=lambda *a, **k: zteClient(*a, scheme="http", **k),
    ):
        return ZteDataCoordinator(mock_hass, entry)


async def _poll(coordinator: ZteDataCoordinator) -> dict:
    coordinator.data = await coordinator._async_update_data()
    return coordinator.data


def _assert_both_connected(coordinator: ZteDataCoordinator) -> None:
    assert coordinator.data["router_info"]["status"] == "connected"
    assert coordinator.is_device_active(MAC_A)
    assert coordinator.is_device_active(MAC_B)


REUSE_MODES = pytest.mark.parametrize(
    "session_reuse", [False, True], ids=["login-per-poll", "session-reuse"]
)


@REUSE_MODES
@pytest.mark.asyncio
async def test_failed_read_does_not_flip_tracked_devices_to_away(
    mock_hass, fake_e2633, session_reuse
) -> None:
    coordinator = _coordinator(mock_hass, fake_e2633, session_reuse=session_reuse)
    await _poll(coordinator)
    _assert_both_connected(coordinator)

    fake_e2633.data_status = 503  # the router answers, but the client list cannot be read
    await _poll(coordinator)
    assert coordinator.available is False
    assert coordinator.data["router_info"]["status"] == "unavailable"
    assert coordinator.is_device_active(MAC_A), "a failed read is not 'device left'"
    assert coordinator.is_device_active(MAC_B)

    fake_e2633.data_status = 200
    await _poll(coordinator)
    assert coordinator.available is True
    _assert_both_connected(coordinator)


@pytest.mark.asyncio
async def test_expired_session_leads_to_a_new_login(mock_hass, fake_e2633) -> None:
    coordinator = _coordinator(mock_hass, fake_e2633, session_reuse=True)
    await _poll(coordinator)
    await _poll(coordinator)
    _assert_both_connected(coordinator)
    assert fake_e2633.login_count == 1, "the session is reused between polls"

    fake_e2633.expire_sessions = 1  # the router forgot our session
    await _poll(coordinator)
    _assert_both_connected(coordinator)
    assert fake_e2633.login_count == 2


@REUSE_MODES
@pytest.mark.asyncio
async def test_recovers_after_the_network_was_gone(
    mock_hass, fake_e2633, session_reuse
) -> None:
    coordinator = _coordinator(mock_hass, fake_e2633, session_reuse=session_reuse)
    await _poll(coordinator)
    _assert_both_connected(coordinator)

    fake_e2633.stop()  # connection refused, like a router that rebooted or lost power
    await _poll(coordinator)
    assert coordinator.available is False
    assert coordinator.is_device_active(MAC_A)
    # A lost connection is not a refused login: no 30 minute pause may be set.
    assert coordinator.client._cmcc_paused_until <= time.monotonic()

    fake_e2633.start()
    await _poll(coordinator)
    assert coordinator.available is True
    _assert_both_connected(coordinator)


@pytest.mark.asyncio
async def test_refused_credentials_are_not_retried_every_poll(
    mock_hass, fake_e2633
) -> None:
    coordinator = _coordinator(mock_hass, fake_e2633, session_reuse=False)
    coordinator.client.password = "wrong-password-used-only-in-this-test"
    for _ in range(3):
        await _poll(coordinator)
        assert coordinator.available is False
    assert fake_e2633.login_count == 1, "the admin account must not be hammered"
