"""Constants for zte_tracker."""

# Base component constants
from homeassistant.const import Platform

DOMAIN = "zte_tracker"
DOMAIN_DATA = f"{DOMAIN}_data"
PLATFORMS = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SWITCH,
    Platform.BUTTON,
]
ISSUE_URL = "https://github.com/juacas/zte_tracker/issues"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
CONF_REGISTER_NEW_DEVICES = "register_new_devices"

STARTUP = """
-------------------------------------------------------------------
{name}
Version: {version}
This is a custom component
If you have any issues with this you need to open an issue here:
{issueurl}
-------------------------------------------------------------------
"""

# Icons
ICON = "mdi:router-wireless"

ICONS = {
    "DesktopComputer": "mdi:desktop-classic",
    "laptop": "mdi:laptop",
    "smartphone": "mdi:cellphone-wireless",
    "game": "mdi:gamepad-variant",
    "stb": "mdi:television",
    "camera": "mdi:cctv",
}

# Defaults
DEFAULT_NAME = "ZTE router tracker"

# Interval in seconds
INTERVAL = 60

# Config options for optional queries
CONF_QUERY_WAN_STATUS = "query_wan_status"
CONF_QUERY_ROUTER_DETAILS = "query_router_details"

# Defaults for optional queries
DEFAULT_QUERY_WAN_STATUS = True
DEFAULT_QUERY_ROUTER_DETAILS = True

# Opt-in flag: keep the router session alive across polls instead of
# logging in/out on every poll. Reduces router auth-log noise dramatically
# on firmwares where the upstream login_need_refresh short-circuit fails
# (e.g. F6600P / Inalan FTTH GR V9.0.10P24N1). Defaults to False so existing
# users keep the original upstream login/fetch/logout flow unchanged.
CONF_SESSION_REUSE = "session_reuse"
DEFAULT_SESSION_REUSE = False

# Opt-in flag: query the mesh topology endpoint for full device visibility
# across all mesh nodes. Requires a separate HTTP session (plain HTTP, not
# HTTPS) to the router. Only effective on models with topo_data_tag config.
CONF_MESH_TOPOLOGY = "mesh_topology"
DEFAULT_MESH_TOPOLOGY = False

# Poll interval preset. 0 is the adaptive 30/60/120 s behaviour, ADAPTIVE_FAST
# the adaptive 10/30/60 s one and ADAPTIVE_RELAXED the adaptive 60/120/300 s
# one. Every poll logs in to the router, which only allows one web session.
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 0
ADAPTIVE_FAST = -1
ADAPTIVE_RELAXED = -2
SCAN_INTERVAL_PRESETS = (ADAPTIVE_FAST, 0, ADAPTIVE_RELAXED)

# Opt-in: poll right after a device announces itself with ARP on the LAN instead of
# waiting for the next interval. Needs raw-socket access on the Home Assistant
# host, so it is off by default.
CONF_JOIN_REFRESH = "join_refresh"
DEFAULT_JOIN_REFRESH = False

# Form-only field of the options flow; only the resulting scan_interval is stored.
