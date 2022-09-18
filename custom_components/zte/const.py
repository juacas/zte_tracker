"""Constants for zte."""
# Base component constants
DOMAIN = "zte"
DOMAIN_DATA = "{}_data".format(DOMAIN)
VERSION = "0.4.1"
PLATFORMS = ["sensor"]
ISSUE_URL = "https://github.com/juacas/zte/issues"

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
DEFAULT_NAME = "ZTE router"

# Interval in seconds
INTERVAL = 60
