# ZTE Router Integration for Home Assistant 
Component to integrate some ZTE routers as a device trackers in home assistant.

## Features
- Provides a device_tracker to monitor the connection status of devices in your Wifi and LAN ports.
- Exposes the status of the scanner in "sensor.zte_tracker".
- Exposes the service "zte_tracker.pause" to pause/resume the scanner because when the scanner is running the web-admin-console sessions are cancelled.

## Compatible routers
|   Name         | Model           | 
| -------------  |:-------------:  | 
| ZTE F6640      | F6640           |   
| ZTE H288A      | H288A           | 
| ZTE H169A      | H169A           |  

This integration could work with more routers. Try one of the above and see if it work with yours.

## Installation

To use this integration, place the following snippet in configuration.yaml. 


```
# Setup the platform zte_tracker
zte_tracker:
     host: 192.168.1.1
     model: F6640
     username: user
     password: !secret zte_password
     interval_seconds: 60
     consider_home: 180
     poll_time: 60
     new_device_defaults:
       track_new_devices: no
```
Change the following parameters to match your configuration:

`host`: Your router's local IP address (Usually 192.168.1.1 or 192.168.0.1)

`username`: Your router's login username (Usually admin)

`password`: Your router's login password 

`model`: Your router's model. Chose one from the Model column of the [table above](#compatible-routers) 


For more information about the device_tracker parameters visit the official [Home Assistant Documentation](https://www.home-assistant.io/integrations/device_tracker/)

## Contributors

- Thanks to @gselivanof for H288A, H169A models.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
