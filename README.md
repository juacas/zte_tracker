# ZTE F6640 Router Integration in Home Assistant
Component to integrate the Huawei ZTE router (tested on model ZTE F6640).

## Features
- Provides a device_tracker to monitor the connection status of devices in your Wifi and LAN ports.
- Exposes the status of the scanner in "sensor.zte_tracker".
- Exposes the service "zte_tracker.pause" to pause/resume the scanner because when the scanner is running the web-admin-console sessions are cancelled.
- TODO: Publish the zte_tracker.reboot service to reboot the router (not implemented yet).

## Example usage

```
# Setup the platform zte_tracker
zte_tracker:
     host: 192.168.1.1
     username: user
     password: !secret zte_password
     interval_seconds: 60
     consider_home: 180
     poll_time: 60
     new_device_defaults:
       track_new_devices: false
```

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
