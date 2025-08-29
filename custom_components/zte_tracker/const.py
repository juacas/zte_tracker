"""Constants for zte_tracker."""

# Base component constants
from homeassistant.const import Platform

DOMAIN = "zte_tracker"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "2.0.1"
PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER, Platform.SWITCH]
ISSUE_URL = "https://github.com/juacas/zte_tracker/issues"
DEFAULT_HOST = "192.168.1.1"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

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
