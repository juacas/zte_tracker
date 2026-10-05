"""Tests for the ARP-triggered refresh."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.zte_tracker import live_refresh
from custom_components.zte_tracker.live_refresh import JoinRefresh

MAC = "aa:bb:cc:dd:ee:01"
IP = "192.168.1.50"


def _refresher(active: bool = False):
    coordinator = SimpleNamespace(
        is_device_active=Mock(return_value=active),
        async_request_refresh=AsyncMock(),
    )
    hass = Mock()
    hass.loop.time.return_value = 1000.0
    return JoinRefresh(hass, coordinator), coordinator


def test_frame_from_active_device_is_ignored() -> None:
    """Traffic from connected devices must not touch the router."""
    refresher, _ = _refresher(active=True)
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, IP)
    call_later.assert_not_called()


def test_frame_from_unknown_device_schedules_one_check() -> None:
    """A burst of frames from the same MAC collapses into one check."""
    refresher, _ = _refresher()
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp("AA:BB:CC:DD:EE:01", IP)
        refresher._handle_arp(MAC, IP)
    assert len(call_later.call_args_list) == 1
    assert call_later.call_args.args[1] == live_refresh.FIRST_CHECK_DELAY


@pytest.mark.asyncio
async def test_check_refreshes_then_retries_once_if_still_inactive() -> None:
    """Refresh after the first delay, then once more if the MAC is still absent."""
    refresher, coordinator = _refresher()
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, IP)
        await call_later.call_args.args[2](None)
        assert coordinator.async_request_refresh.await_count == 1
        assert call_later.call_args.args[1] == live_refresh.SECOND_CHECK_DELAY

        await call_later.call_args.args[2](None)

    assert coordinator.async_request_refresh.await_count == 2
    assert refresher._pending == {}


@pytest.mark.asyncio
async def test_second_check_is_skipped_once_device_is_active() -> None:
    """No extra poll when the first refresh already found the device."""
    refresher, coordinator = _refresher()
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, IP)
        await call_later.call_args.args[2](None)
        coordinator.is_device_active.return_value = True
        await call_later.call_args.args[2](None)

    assert coordinator.async_request_refresh.await_count == 1


def test_start_and_stop_the_listener() -> None:
    """Enabling starts the listener once; disabling stops it and cancels checks."""
    refresher, _ = _refresher()
    arp_stop = Mock()
    cancel = Mock()
    with patch.object(
        live_refresh, "async_start_arp", return_value=arp_stop
    ) as start_arp:
        refresher.async_set_enabled(True)
        refresher.async_set_enabled(True)
        assert refresher.running
        start_arp.assert_called_once()

        refresher._pending[MAC] = [cancel]
        refresher.async_set_enabled(False)

    arp_stop.assert_called_once()
    cancel.assert_called_once()
    assert not refresher.running
    assert refresher._pending == {}


def test_start_failure_is_logged_not_raised(caplog) -> None:
    """Polling keeps working when raw sockets are not available."""
    refresher, _ = _refresher()
    with patch.object(live_refresh, "async_start_arp", side_effect=OSError("no")):
        refresher.async_set_enabled(True)
    assert not refresher.running
    assert "Join refresh could not start" in caplog.text


def test_failing_stop_still_cleans_up(caplog) -> None:
    """A stop() error is logged and pending checks are still cancelled."""
    refresher, _ = _refresher()
    cancel = Mock()
    with patch.object(
        live_refresh, "async_start_arp", return_value=Mock(side_effect=OSError("x"))
    ):
        refresher.async_set_enabled(True)
    refresher._pending[MAC] = [cancel]
    refresher.async_shutdown()
    assert not refresher.running
    cancel.assert_called_once()
    assert "could not stop" in caplog.text


@pytest.mark.asyncio
async def test_mac_the_router_never_lists_is_ignored_for_a_while() -> None:
    """The router's own ARP must not cause a poll on every frame."""
    refresher, coordinator = _refresher()
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, "192.168.1.1")
        await call_later.call_args.args[2](None)
        await call_later.call_args.args[2](None)
        assert coordinator.async_request_refresh.await_count == 2
        call_later.reset_mock()

        refresher._handle_arp(MAC, "192.168.1.1")
        call_later.assert_not_called()

        refresher._hass.loop.time.return_value += live_refresh.IGNORE_AFTER_MISS + 1
        refresher._handle_arp(MAC, "192.168.1.1")
        call_later.assert_called_once()


@pytest.mark.asyncio
async def test_device_that_appears_on_the_last_poll_is_not_ignored() -> None:
    """Only a MAC still inactive after the second poll gets ignored."""
    refresher, coordinator = _refresher()

    async def _device_appears() -> None:
        coordinator.is_device_active.return_value = True

    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, IP)
        await call_later.call_args.args[2](None)
        coordinator.async_request_refresh.side_effect = _device_appears
        await call_later.call_args.args[2](None)
    assert MAC not in refresher._ignored


def test_a_failing_handler_is_logged_not_raised(caplog) -> None:
    """A bug while handling one frame must not stop the listener."""
    refresher, coordinator = _refresher()
    coordinator.is_device_active.side_effect = RuntimeError("boom")
    refresher._handle_arp(MAC, IP)
    assert "Join refresh failed to handle ARP" in caplog.text


@pytest.mark.asyncio
async def test_failed_poll_is_logged_and_does_not_leave_the_mac_pending(
    caplog,
) -> None:
    """A poll error is logged and the second check still runs."""
    refresher, coordinator = _refresher()
    coordinator.async_request_refresh.side_effect = RuntimeError("router down")
    with patch.object(live_refresh, "async_call_later") as call_later:
        refresher._handle_arp(MAC, IP)
        await call_later.call_args.args[2](None)
        assert "Join refresh could not poll the router" in caplog.text
        await call_later.call_args.args[2](None)
    assert MAC not in refresher._pending
    assert MAC in refresher._ignored
