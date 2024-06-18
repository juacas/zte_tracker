![GitHub](https://img.shields.io/github/license/juacas/zte_tracker)
![GitHub Repo stars](https://img.shields.io/github/stars/juacas/zte_tracker)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/juacas/zte_tracker)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
<!-- ![Pytest](https://github.com/juacas/zte_tracker/workflows/Pytest/badge.svg?branch=master)
![CodeQL](https://github.com/juacas/zte_tracker/workflows/CodeQL/badge.svg?branch=master) -->
![Validate with hassfest](https://github.com/juacas/zte_tracker/workflows/Validate%20with%20hassfest/badge.svg?branch=master)

![GitHub contributors](https://img.shields.io/github/contributors/juacas/zte_tracker)
![Maintenance](https://img.shields.io/maintenance/yes/2025)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/juacas/zte_tracker)
![GitHub commits since tagged version](https://img.shields.io/github/commits-since/juacas/zte_tracker/v1.0.0)
![GitHub last commit](https://img.shields.io/github/last-commit/juacas/zte_tracker)
<!-- ![Codecov branch](https://img.shields.io/codecov/c/github/juacas/zte_tracker/master) -->
![installation_badge](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.zte_tracker.total)

# ZTE Router Integration for Home Assistant
Component to integrate some ZTE routers as a device trackers in home assistant.

## Features
- Provides a device_tracker to monitor the connection status of devices in your Wifi and LAN ports.
- Exposes the status of the scanner in "sensor.zte_tracker".
- Exposes the service "zte_tracker.pause" to pause/resume the scanner because when the scanner is running the web-admin-console sessions are cancelled.

## Compatible routers
|   Name         | Model Param     |
| -------------  |:-------------:  |
| ZTE F6640      | F6640           |
| ZTE F6645P     | F6640P          |
| ZTE H169A      | H169A           |
| ZTE H2640      | H2640           |
| ZTE H288A      | H288A           |
| ZTE H388X      | H388X           |
| ZTE H3600P     | H3600P          |
| ZTE H3640 V10  | H3640           |
| ZTE H6645P V2  | H6645P          |


This integration could work with more routers. Try one of the above and see if it works with yours.

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

- Thanks to @gselivanof for H288A, H169A models support, @TrinTragula for H388X verification, @kvshino for H2640 verification, @dapuzz for G6645P verification, @onegambler for H3600P verification, @lapo for H6645P verification, @309631 for H3640 verification.
