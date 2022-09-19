# ZTE Router Integration in Home Assistant
Component to integrate the Huawei ZTE router (tested on model ZTE F6640).

## Features
- Publish the zte.reboot service to reboot the router.
- Provides a device_tracker to monitor the connection status of devices.

## Example usage

```
# Setup the platform zte
zte:
  host: 192.168.0.1
  username: admin
  password: !secret router_password

# Enable and customize the tracker's parameters
device_tracker:
- platform: zte
  interval_seconds: 60
  consider_home: 180
  new_device_defaults:
    track_new_devices: false
```

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
