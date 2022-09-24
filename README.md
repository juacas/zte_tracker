# ZTE F6640 Router Integration in Home Assistant
Component to integrate the Huawei ZTE router (tested on model ZTE F6640).

## Features
- Provides a device_tracker to monitor the connection status of devices in your Wifi and LAN ports.
- TODO: Publish the zte.reboot service to reboot the router (not implemented yet).

## Example usage

Place this fragment in configuration.yaml (adapting host, username and password) to your setup).

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
