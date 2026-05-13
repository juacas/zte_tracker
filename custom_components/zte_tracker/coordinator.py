"""Data coordinator for ZTE Tracker integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_MESH_TOPOLOGY,
    CONF_QUERY_ROUTER_DETAILS,
    CONF_QUERY_WAN_STATUS,
    CONF_REGISTER_NEW_DEVICES,
    CONF_SESSION_REUSE,
    DEFAULT_MESH_TOPOLOGY,
    DEFAULT_SESSION_REUSE,
    DOMAIN,
)
from .zteclient.zte_client import zteClient

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)
FAST_UPDATE_INTERVAL = timedelta(seconds=30)
SLOW_UPDATE_INTERVAL = timedelta(seconds=120)

# Force a fresh login if our cached session is older than this. Polling every
# 30-120s keeps the session active so the router shouldn't naturally idle-time
# us out, but routers may force-expire sessions on a max-age timer. 30 min is
# a safe middle ground: low enough to avoid hitting most max-age limits,
# high enough to drop auth-log noise from ~120/hr (per-poll spam) to ~2/hr.
# The retry-once path below catches sessions that die earlier.
SESSION_MAX_AGE = timedelta(minutes=30)


class ZteDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ZTE router data with intelligent caching."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        # Resolve flags: options take precedence over data, then defaults
        query_wan = entry.options.get(
            CONF_QUERY_WAN_STATUS, entry.data.get(CONF_QUERY_WAN_STATUS)
        )
        query_router = entry.options.get(
            CONF_QUERY_ROUTER_DETAILS, entry.data.get(CONF_QUERY_ROUTER_DETAILS)
        )

        # Ensure booleans with sensible defaults if None
        query_wan = bool(query_wan) if query_wan is not None else True
        query_router = bool(query_router) if query_router is not None else True

        self._mesh_topology = bool(
            entry.options.get(
                CONF_MESH_TOPOLOGY,
                entry.data.get(CONF_MESH_TOPOLOGY, DEFAULT_MESH_TOPOLOGY),
            )
        )

        self.client = zteClient(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_MODEL],
            verify_ssl=False,
            query_wan_status=query_wan,
            query_router_details=query_router,
            mesh_topology=self._mesh_topology,
        )
        self._available = True
        self._paused = False
        self._register_new_devices = entry.options.get(CONF_REGISTER_NEW_DEVICES, True)
        self._last_device_count = 0
        self._stable_count = 0
        self._device_cache: dict[str, dict[str, Any]] = {}
        self._last_successful_update: datetime | None = None
        self._last_login_at: datetime | None = None
        self._client_lock = asyncio.Lock()
        self._reuse_session = bool(
            entry.options.get(
                CONF_SESSION_REUSE,
                entry.data.get(CONF_SESSION_REUSE, DEFAULT_SESSION_REUSE),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
            config_entry=entry,
        )

    @property
    def available(self) -> bool:
        """Return if the router is available."""
        return self._available

    @property
    def paused(self) -> bool:
        """Return if scanning is paused."""
        return self._paused

    @property
    def register_new_devices(self) -> bool:
        """Return if new devices should be registered as entities."""
        return self._register_new_devices

    def pause_scanning(self) -> None:
        """Pause device scanning.

        Schedules the logout in the executor so we never block the event loop
        on router I/O, and serializes against the polling loop via the client
        lock.
        """
        self._paused = True
        _LOGGER.info("ZTE tracker scanning paused")

        async def _bg_logout() -> None:
            async with self._client_lock:
                try:
                    await asyncio.wait_for(
                        self.hass.async_add_executor_job(self.client.logout),
                        timeout=5,
                    )
                except Exception as ex:  # noqa: BLE001
                    _LOGGER.debug("pause_scanning logout error: %s", ex)
                self._last_login_at = None

        self.hass.async_create_background_task(_bg_logout(), "zte_tracker_pause_logout")

    def resume_scanning(self) -> None:
        """Resume device scanning.

        Forces a clean client-side session reset so the next poll starts
        with a fresh login, even if the background logout during pause
        failed or the router still holds a stale session.

        We only clear login_data (not session) to avoid racing with a
        background logout that may still be using the session object.
        The login() method sees login_data=None and calls _setup_session()
        which safely replaces any stale session.
        """
        self._paused = False
        self._last_login_at = None
        self.client.login_data = None
        _LOGGER.info("ZTE tracker scanning resumed (session state cleared)")

    def enable_register_new_devices(self) -> None:
        """Enable automatic registration of new devices."""
        self._register_new_devices = True
        _LOGGER.info("ZTE tracker will register new devices")

    def disable_register_new_devices(self) -> None:
        """Disable automatic registration of new devices."""
        self._register_new_devices = False
        _LOGGER.info("ZTE tracker will not register new devices")

    def _adjust_update_interval(self, device_count: int) -> None:
        """Adjust update interval based on device activity."""
        if device_count == self._last_device_count:
            self._stable_count += 1
        else:
            self._stable_count = 0
            self._last_device_count = device_count

        # If devices are stable for a while, slow down polling
        if self._stable_count > 5:
            new_interval = SLOW_UPDATE_INTERVAL
        elif self._stable_count < 2:
            new_interval = FAST_UPDATE_INTERVAL
        else:
            new_interval = DEFAULT_UPDATE_INTERVAL

        if self.update_interval != new_interval:
            _LOGGER.debug(
                "Adjusting update interval from %s to %s (stable count: %d)",
                self.update_interval,
                new_interval,
                self._stable_count,
            )
            self.update_interval = new_interval

    async def async_reboot_router(self) -> bool:
        """Reboot the router."""

        def _reboot():
            try:
                return self.client.reboot()
            except Exception as ex:
                _LOGGER.error("Failed to reboot router: %s", ex)
                return False

        async with self._client_lock:
            result = await self.hass.async_add_executor_job(_reboot)
            # Reboot invalidates any session we held.
            self._last_login_at = None
            return result

    def _enrich_topology(
        self,
        topo_devices: list[dict[str, Any]],
        legacy_devices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich topology devices with SSID and metadata from legacy data.

        Only replaces legacy list if topology has at least as many devices.
        """
        # Safety: don't replace if topology returned fewer devices
        if len(topo_devices) < len(legacy_devices):
            _LOGGER.warning(
                "Topology has fewer devices (%d) than legacy (%d); using legacy",
                len(topo_devices),
                len(legacy_devices),
            )
            return legacy_devices

        legacy_by_mac = {d.get("MACAddress", ""): d for d in legacy_devices}

        # Phase 1: merge known fields by MAC
        for td in topo_devices:
            legacy = legacy_by_mac.get(td.get("MACAddress", ""))
            if legacy:
                if legacy.get("Port"):
                    td["Port"] = legacy["Port"]
                if legacy.get("ConnectTime"):
                    td["ConnectTime"] = legacy["ConnectTime"]
                if legacy.get("LinkTime"):
                    td["LinkTime"] = legacy["LinkTime"]

        # Phase 2: propagate SSID to agent devices by AccessType
        ssid_by_access: dict[str, str] = {}
        for td in topo_devices:
            port = td.get("Port", "")
            access = td.get("_AccessType", "")
            if port and access and access not in ssid_by_access:
                ssid_by_access[access] = port
        for td in topo_devices:
            if not td.get("Port") and td.get("_AccessType"):
                td["Port"] = ssid_by_access.get(td["_AccessType"], "")

        _LOGGER.info(
            "Mesh topology: %d devices (was %d from legacy)",
            len(topo_devices),
            len(legacy_devices),
        )
        return topo_devices

    def _merge_device_data(self, new_devices: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge new device data with cached data for better stability."""
        processed_devices = {}

        # Update cache with new data
        current_macs = set()
        for device in new_devices:
            mac = device.get("MACAddress")
            if not mac:
                continue

            current_macs.add(mac)
            device_data = {
                "name": device.get("HostName", "Unknown"),
                "ip": device.get("IPAddress", ""),
                "mac": mac,
                "active": device.get("Active", False),
                "icon_type": device.get("IconType"),
                "network_type": device.get("NetworkType", "Unknown"),
                "last_seen": datetime.now().isoformat(),
                "port": device.get("Port", ""),  # LAN port or WLAN ESSID
                "LinkTime": device.get("LinkTime", ""),
                "ConnectTime": device.get("ConnectTime", ""),
                "mesh_node": device.get("MeshNode", ""),
            }

            # Merge with cached data if available
            if mac in self._device_cache:
                cached = self._device_cache[mac]
                # Keep the name if new one is generic and cached one is better
                if device_data["name"] in ("Unknown", mac) and cached.get(
                    "name", "Unknown"
                ) not in ("Unknown", mac):
                    device_data["name"] = cached["name"]

                # Keep last_seen from cache if device is not currently active
                if not device_data["active"] and cached.get("last_seen"):
                    device_data["last_seen"] = cached["last_seen"]

            self._device_cache[mac] = device_data
            processed_devices[mac] = device_data

        # Mark devices not seen in this scan as inactive but keep in cache
        for mac, cached_device in self._device_cache.items():
            if mac not in current_macs:
                # Keep device in processed list but mark as inactive
                inactive_device = cached_device.copy()
                inactive_device["active"] = False
                processed_devices[mac] = inactive_device

        return processed_devices

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the router."""
        if self._paused:
            _LOGGER.debug("Scanning paused, returning cached data")
            # Return cached data when paused
            return {
                "devices": {
                    mac: data.copy() for mac, data in self._device_cache.items()
                },
                "router_info": {
                    "host": self.client.host,
                    "model": self.client.model,
                    "status": "paused",
                },
            }

        def _fetch_router_data_legacy() -> tuple[
            list[dict[str, Any]] | None,
            dict[str, Any] | None,
            dict[str, Any] | None,
        ]:
            """Original upstream fetch path: login -> fetch -> logout per poll.

            Used when the session_reuse option is disabled (default) so we
            don't change behaviour for users who haven't opted in to the
            session-reuse experiment.
            """
            try:
                if not self.client.login():
                    _LOGGER.warning(
                        "Login failed: %s@%s", self.client.username, self.client.host
                    )
                    return None, None, None

                devices = self.client.get_devices_response()
                wanstatus = self.client.get_wan_status()
                routerdetails = self.client.get_router_details()

                # Mesh topology enrichment (before logout!)
                if devices is not None and self._mesh_topology:
                    topo = self.client._try_topology()
                    if topo:
                        devices = self._enrich_topology(topo, devices)

                return devices, wanstatus, routerdetails
            except Exception as ex:
                _LOGGER.error("Error fetching device data: %s", ex)
                return None, None, None
            finally:
                try:
                    self.client.logout()
                except Exception:
                    pass

        def _fetch_router_data_reuse() -> tuple[
            list[dict[str, Any]] | None,
            dict[str, Any] | None,
            dict[str, Any] | None,
        ]:
            """Session-reuse fetch path (opt-in via the session_reuse option).

            Reuses the existing client session across polls to avoid spamming
            the router auth log with login/logout pairs. If the cached session
            is stale (router idle-timed it out), the first fetch will fail; we
            then force a logout+login and retry once within the same cycle so
            we don't burn a whole polling interval on a recoverable hiccup.
            """

            # Proactive session refresh: if we've been holding the same
            # session longer than SESSION_MAX_AGE, force a clean re-login
            # before the router idle-times us out and the first attempt
            # below silently fails.
            now = datetime.now()
            if (
                self._last_login_at is not None
                and now - self._last_login_at > SESSION_MAX_AGE
            ):
                _LOGGER.debug(
                    "Session age %s exceeds %s; proactively re-authenticating",
                    now - self._last_login_at,
                    SESSION_MAX_AGE,
                )
                try:
                    self.client.logout()
                except Exception:
                    pass
                self._last_login_at = None

            def _attempt() -> tuple[
                list[dict[str, Any]] | None,
                dict[str, Any] | None,
                dict[str, Any] | None,
                bool,
            ]:
                try:
                    have_session = (
                        self.client.login_data is not None
                        and self.client.session is not None
                        and self._last_login_at is not None
                    )

                    if have_session:
                        _LOGGER.debug("Reusing existing router session")
                    else:
                        if not self.client.login():
                            _LOGGER.debug(
                                "Login failed: %s@%s",
                                self.client.username,
                                self.client.host,
                            )
                            return None, None, None, False
                        _LOGGER.debug("Fresh router login established")
                        self._last_login_at = datetime.now()

                    devices = self.client.get_devices_response()
                    if devices is None:
                        return None, None, None, False

                    # Stale-session safety net: if we reused a cached session
                    # and got back an empty device list, the router likely
                    # served us a redirect-to-login page (HTTP 200 with login
                    # HTML) instead of real data. Real-world router always has
                    # at least the HA host itself + the gateway visible, so an
                    # empty list on a reused session is a strong stale-session
                    # signal -> trigger the retry-once path with a fresh login.
                    if have_session and len(devices) == 0:
                        _LOGGER.debug(
                            "Empty device list on reused session; treating as stale"
                        )
                        return None, None, None, False

                    wanstatus = self.client.get_wan_status()
                    routerdetails = self.client.get_router_details()

                    # Mesh topology enrichment (session still alive)
                    if devices is not None and self._mesh_topology:
                        topo = self.client._try_topology()
                        if topo:
                            devices = self._enrich_topology(topo, devices)

                    return devices, wanstatus, routerdetails, True
                except Exception as ex:
                    _LOGGER.debug("Fetch attempt error: %s", ex)
                    return None, None, None, False

            devices, wanstatus, routerdetails, ok = _attempt()

            if not ok:
                _LOGGER.debug(
                    "Initial fetch failed; reauthenticating and retrying once"
                )
                try:
                    self.client.logout()
                except Exception:
                    pass
                self._last_login_at = None
                devices, wanstatus, routerdetails, ok = _attempt()
                if not ok:
                    _LOGGER.warning(
                        "Login/fetch failed after retry: %s@%s",
                        self.client.username,
                        self.client.host,
                    )
                    # Clear session state so next cycle starts fresh
                    try:
                        self.client.logout()
                    except Exception:
                        pass
                    self._last_login_at = None

            return devices, wanstatus, routerdetails

        _fetch_router_data = (
            _fetch_router_data_reuse if self._reuse_session else _fetch_router_data_legacy
        )

        async with self._client_lock:
            devices, wanstatus, routerdetails = await self.hass.async_add_executor_job(
                _fetch_router_data
            )

        if devices is None:
            self._available = False
            devicesItem = {}
            # Return cached data on failure if we have it and it's recent
            if (
                self._device_cache
                and self._last_successful_update
                and datetime.now() - self._last_successful_update
                < timedelta(minutes=10)
            ):
                _LOGGER.warning("Using cached data due to connection failure")
                devicesItem = {
                    mac: data.copy() for mac, data in self._device_cache.items()
                }

            return {
                "devices": devicesItem,
                "router_info": {
                    "host": self.client.host,
                    "model": self.client.model,
                    "status": "unavailable",
                },
            }

        # Have info to return. Tracker is working.
        self._available = True
        self._last_successful_update = datetime.now()

        # Process devices with caching
        processed_devices = self._merge_device_data(devices)

        # Adjust polling interval based on device activity
        active_count = len([d for d in processed_devices.values() if d.get("active")])
        self._adjust_update_interval(active_count)

        router_info = {
            "host": self.client.host,
            "model": self.client.model,
            "status": "connected",
            "last_update": self._last_successful_update.isoformat(),
            "active_devices": active_count,
            "total_devices": len(processed_devices),
        }
        if wanstatus:
            router_info.update(wanstatus)
        if routerdetails:
            router_info.update(routerdetails)
        return {
            "devices": processed_devices,
            "router_info": router_info,
        }
