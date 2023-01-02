# ZTE H288A Router Integration in Home Assistant (WORK IN PROGRESS)
Component to integrate the ZTE H288A router as a device tracker in home assistant.

## Features
- Provides a device_tracker to monitor the connection status of devices in your Wifi and LAN ports.
- Exposes the status of the scanner in "sensor.zte_tracker".
- Exposes the service "zte_tracker.pause" to pause/resume the scanner because when the scanner is running the web-admin-console sessions are cancelled.

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
       track_new_devices: no
```
