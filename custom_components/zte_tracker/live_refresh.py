"""Refresh the router data as soon as a device joins the network.

The router exposes no push channel (no usable syslog, and its TR-069 client is
bound to the WAN), but a device that joins the network announces itself with an
ARP frame, which Home Assistant can hear. That triggers an immediate poll
instead of waiting for the next interval. Only devices the router does not
already list as active trigger a poll, so traffic from connected devices costs
the router nothing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .arp_watcher import async_start_arp

if TYPE_CHECKING:
    from .coordinator import ZteDataCoordinator

_LOGGER = logging.getLogger(__name__)

# Let the router register the client before asking for it.
FIRST_CHECK_DELAY = 3
# One follow-up for slow association, then give up until the next event.
SECOND_CHECK_DELAY = 10
# A MAC the router still does not list after both checks (the router itself,
# a container or VM interface, ...) is ignored for a while so it cannot cause
# a poll on every frame it sends.
IGNORE_AFTER_MISS = 3600


class JoinRefresh:
    """Listen for ARP frames and refresh for new clients."""

    def __init__(self, hass: HomeAssistant, coordinator: ZteDataCoordinator) -> None:
        """Initialize the listener, which stays idle until enabled."""
        self._hass = hass
        self._coordinator = coordinator
        self._stop_arp: CALLBACK_TYPE | None = None
        self._pending: dict[str, list[CALLBACK_TYPE]] = {}
        self._ignored: dict[str, float] = {}

    @property
    def running(self) -> bool:
        """Return True while the ARP listener is active."""
        return self._stop_arp is not None

    @callback
    def async_set_enabled(self, enabled: bool) -> None:
        """Start or stop listening."""
        if enabled:
            self._start()
        else:
            self.async_shutdown()

    def _start(self) -> None:
        if self.running:
            return
        try:
            self._stop_arp = async_start_arp(self._hass.loop, self._handle_arp)
        except Exception as ex:  # noqa: BLE001 - never break setup
            _LOGGER.warning("Join refresh could not start, polling only: %s", ex)
            return
        _LOGGER.info("Join refresh enabled")

    @callback
    def async_shutdown(self) -> None:
        """Stop listening and cancel pending checks."""
        if self._stop_arp is not None:
            stop, self._stop_arp = self._stop_arp, None
            try:
                stop()
            except Exception:  # noqa: BLE001 - always finish the cleanup
                _LOGGER.exception("Join refresh could not stop the ARP listener")
            else:
                _LOGGER.info("Join refresh disabled")
        for cancels in self._pending.values():
            for cancel in cancels:
                cancel()
        self._pending.clear()
        self._ignored.clear()

    @callback
    def _handle_arp(self, mac: str, ip: str) -> None:
        """Handle one ARP frame seen on the LAN."""
        try:
            self._schedule(mac, f"ARP from {ip}")
        except Exception:  # noqa: BLE001 - a bad frame must not stop the listener
            _LOGGER.exception("Join refresh failed to handle ARP from %s", ip)

    def _schedule(self, mac: str, source: str) -> None:
        mac = mac.lower()
        if not mac or mac in self._pending:
            return
        now = self._hass.loop.time()
        if self._ignored.get(mac, 0) > now:
            return
        if self._coordinator.is_device_active(mac):
            return
        _LOGGER.debug(
            "%s from %s which the router does not list as active, refreshing",
            source,
            mac,
        )
        self._pending[mac] = [
            async_call_later(self._hass, FIRST_CHECK_DELAY, self._first_check(mac))
        ]

    def _first_check(self, mac: str):
        async def _run(_now: Any) -> None:
            await self._refresh()
            if self._pending.get(mac) is None:
                return
            self._pending[mac] = [
                async_call_later(
                    self._hass, SECOND_CHECK_DELAY, self._second_check(mac)
                )
            ]

        return _run

    def _second_check(self, mac: str):
        async def _run(_now: Any) -> None:
            self._pending.pop(mac, None)
            if self._coordinator.is_device_active(mac):
                return
            await self._refresh()
            if not self._coordinator.is_device_active(mac):
                self._ignored[mac] = self._hass.loop.time() + IGNORE_AFTER_MISS

        return _run

    async def _refresh(self) -> None:
        # A failed poll must not leave the MAC stuck as pending.
        try:
            await self._coordinator.async_request_refresh()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Join refresh could not poll the router")
