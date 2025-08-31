# Release Notes

## v2.0.3

- Added router reboot service: `zte_tracker.reboot` to remotely reboot the router.
- Added service to remove all device_tracker entities without a unique ID for easier cleanup.
- Improved router details: sensor attributes now include model, firmware, uptime, CPU load, Memory usage, and useful WAN info.
- Documentation updates for reboot service and enhanced attribute reporting.
- Minor bug fixes and code quality improvements.

## v2.0.2

- Enhanced error handling and logging for device tracker and sensor platforms.
- Improved compatibility with additional ZTE router models.
- Updated documentation and HACS metadata.

## v2.0.1

- Fixed device persistence issues for temporary network disconnections.
- Improved adaptive polling intervals for better network stability.
- Minor fixes for device naming and icon selection.

## v2.0.0

### Main Features

- **Device Tracking:** Real-time monitoring for WiFi and LAN connections, smart device naming, and network type detection.
- **Router Management:** Router status sensors with WAN health indicators, remote reboot capability via service call, and pause/resume scanning.
- **Router Details:** Sensor attributes now provide comprehensive router information (model, firmware, uptime, WAN status, etc.).
- **Performance & Reliability:** Adaptive polling, intelligent caching, connection pooling, and robust error handling.
- **Modern Home Assistant Integration:** Config Flow support, Device Registry integration, DataUpdateCoordinator usage, and HACS compatibility.
- **Services:**
  - `zte_tracker.reboot`: Remotely reboot the router.
  - `zte_tracker.remove_tracked_entity`: Remove a tracked device by MAC address.
  - `zte_tracker.remove_unidentified_entities`: Remove all device_tracker entities without a unique ID.
- **Supported Routers:** F6640, H288A, H169A, H388X, H2640, F6645P, H3600P, H6645P, H3640.

---
For installation and usage instructions,