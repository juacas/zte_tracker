"""Constants for zte_tracker."""
# Base component constants
from unittest.mock import DEFAULT


DOMAIN = "zte_tracker"
DOMAIN_DATA = "{}_data".format(DOMAIN)
VERSION = "1.3.4"
PLATFORMS = ["sensor", "device_tracker"]
ISSUE_URL = "https://github.com/juacas/zte_tracker/issues"
DEFAULT_HOST = '192.168.1.1'
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'

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
    'DesktopComputer': 'mdi:desktop-classic',
    'laptop': 'mdi:laptop',
    'smartphone': 'mdi:cellphone-wireless',
    'game': 'mdi:gamepad-variant',
    'stb': 'mdi:television',
    'camera': 'mdi:cctv'
}
# Configuration
# CONF_NAME = "name"
# CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_NAME = "ZTE router tracker"

# Interval in seconds
INTERVAL = 60
