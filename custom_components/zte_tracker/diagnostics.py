"""Diagnostics support for the ZTE router integration."""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .support_bundle import BUNDLE_DIRNAME
from .support_shape import is_sensitive_name

TO_REDACT = {CONF_HOST, CONF_PASSWORD, CONF_USERNAME, "statusmsg"}

# Allowlist, not denylist.
_ALLOWED_KEY = re.compile(
    r"^(cpu\w*|mem\w*|poweron\w*|uptime|last_update|\w*_?leasetime"
    r"|(wan_)?(conn)?(status|state|mode|rate|errors|packets|bytes|margin"
    r"|attenuation|delay|depth|module_type|retrain|showtime|enabled?"
    r"|error_message|error)"
    r"|\w+_(status|state|rate|errors|packets|bytes|uptime|connected|traffic))$",
    re.IGNORECASE,
)

_IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6 = re.compile(
    r"(?<![0-9A-Za-z:.])"
    r"(?:(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}"
    r"|(?:[0-9a-f]{1,4}:){1,7}:(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,6})?)"
    r"(?:/\d{1,3})?(?![0-9A-Za-z:.])",
    re.IGNORECASE,
)
_MAC = re.compile(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", re.IGNORECASE)
_MAC_DOTTED = re.compile(r"\b[0-9a-f]{4}(?:\.[0-9a-f]{4}){2}\b", re.IGNORECASE)
_URI = re.compile(
    r"\b(?:sips?|tel)\s*:\s*[^\s<>\"']+|\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b",
    re.IGNORECASE,
)


def _scrub_value(key: str, value: Any) -> Any:
    """Keep a router attribute only if its name is known to be non-identifying."""
    # A sensitive name is sensitive whatever the type: SerialNumber arriving as
    # an int, or a WPS PIN, went out in clear when numbers were trusted wholesale.
    if is_sensitive_name(key):
        return "**REDACTED**"
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    # Each token is anchored.
    if not _ALLOWED_KEY.match(key):
        return "**REDACTED**"
    if isinstance(value, str):
        # An allowed key can still carry an identifier inside free text, and
        # WAN_error_message is kept precisely because it is free text.
        for pattern in (_IPV6, _IPV4, _MAC, _MAC_DOTTED, _URI):
            value = pattern.sub("**REDACTED**", value)
    return value


def _scrub_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {key: _scrub_value(key, value) for key, value in data.items()}


def _device_summary(devices: dict[str, Any]) -> dict[str, Any]:
    """Aggregate the device list without emitting any device identity."""
    by_network: Counter[str] = Counter()
    keys_seen: set[str] = set()
    active = 0
    named = 0
    with_mesh_node = 0

    for record in devices.values():
        if not isinstance(record, dict):
            continue
        keys_seen.update(record)
        by_network[str(record.get("network_type", "Unknown"))] += 1
        if record.get("active"):
            active += 1
        if record.get("name") not in (None, "", "Unknown"):
            named += 1
        if record.get("mesh_node"):
            with_mesh_node += 1

    return {
        "total": len(devices),
        "active": active,
        "with_hostname": named,
        "with_mesh_node": with_mesh_node,
        "by_network_type": dict(by_network),
        "record_keys": sorted(keys_seen),
    }


_NO_BUNDLE = {
    "present": False,
    "hint": (
        "Run the zte_tracker.export_support_bundle action if this is a request "
        "for a router model that is not supported yet."
    ),
}


def _support_bundle_hint(hass: HomeAssistant) -> dict[str, Any]:
    """Whether a support bundle exists, and how old. Never its contents."""
    directory = hass.config.path(BUNDLE_DIRNAME)
    try:
        names = [
            name
            for name in os.listdir(directory)
            if name.startswith("export-") and name.endswith(".json")
        ]
    except OSError:
        return _NO_BUNDLE
    if not names:
        return _NO_BUNDLE
    newest = max(os.path.getmtime(os.path.join(directory, name)) for name in names)
    return {
        "present": True,
        "count": len(names),
        "newest_age_minutes": round((time.time() - newest) / 60),
        "directory": BUNDLE_DIRNAME,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    diagnostics: dict[str, Any] = {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        }
    }

    if coordinator is None:
        diagnostics["error"] = "coordinator not loaded"
        return diagnostics

    client = getattr(coordinator, "client", None)
    data = coordinator.data or {}
    router_info = dict(data.get("router_info") or {})

    # The endpoint profile is the single most useful field in a support
    # request: it says which of the five distinct _MODELS profiles the router was driven
    profile = dict(getattr(client, "paths", {}) or {}) if client else {}

    diagnostics["router"] = {
        "model_configured": getattr(client, "model", None),
        "model_reported": router_info.get("ModelName"),
        "hardware_version": router_info.get("HardwareVer"),
        "firmware_version": router_info.get("SoftwareVer"),
        "manufacturer": router_info.get("ManuFacturer"),
        "profile": profile,
        "scheme": profile.get("default_scheme"),
        "status": router_info.get("status"),
        "verify_ssl": getattr(client, "verify_ssl", None),
    }

    diagnostics["coordinator"] = {
        "available": getattr(coordinator, "_available", None),
        "paused": getattr(coordinator, "_paused", None),
        "session_reuse": bool(getattr(coordinator, "_reuse_session", False)),
        "mesh_topology": bool(getattr(coordinator, "_mesh_topology", False)),
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None
        ),
        "last_update_success": coordinator.last_update_success,
        "cached_devices": len(getattr(coordinator, "_device_cache", {}) or {}),
        "topology_failures": getattr(client, "_topo_failures", 0),
    }

    # A pointer, not the contents.
    diagnostics["support_bundle"] = _support_bundle_hint(hass)

    # Everything the router reported that is not identity: CPU, memory, uptime,
    # WAN link state, traffic counters.
    diagnostics["router_attributes"] = _scrub_mapping(
        {
            key: value
            for key, value in router_info.items()
            if key
            not in {
                "ModelName",
                "HardwareVer",
                "SoftwareVer",
                "ManuFacturer",
                "status",
                "model",
                # coordinator.py puts the configured host here.
                "host",
            }
        }
    )

    diagnostics["devices"] = _device_summary(data.get("devices") or {})

    return diagnostics
