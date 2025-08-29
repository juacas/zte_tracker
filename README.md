![GitHub](https://img.shields.io/github/license/juacas/zte_tracker)
![GitHub Repo stars](https://img.shields.io/github/stars/juacas/zte_tracker)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/juacas/zte_tracker)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![Validate with hassfest](https://github.com/juacas/zte_tracker/workflows/Validate%20with%20hassfest/badge.svg?branch=master)

![GitHub contributors](https://img.shields.io/github/contributors/juacas/zte_tracker)
![Maintenance](https://img.shields.io/maintenance/yes/2025)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/juacas/zte_tracker)
![GitHub commits since tagged version](https://img.shields.io/github/commits-since/juacas/zte_tracker/v1.0.0)
![GitHub last commit](https://img.shields.io/github/last-commit/juacas/zte_tracker)
![installation_badge](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.zte_tracker.total)

# ZTE Router Integration for Home Assistant

A modern, feature-rich integration for ZTE routers that provides comprehensive device tracking and router management capabilities for Home Assistant.

## ✨ Features

### Device Tracking

- **Real-time device monitoring** for both WiFi and LAN connections
- **Intelligent device persistence** - devices remain tracked even during temporary disconnections
- **Smart device naming** with fallback to cached names for better identification
- **Network type detection** (WiFi/LAN) with appropriate icons

### Router Management

- **Router status monitoring** with connection health indicators
- **Remote router reboot** capability through service calls (Unimplemented)
- **Pause/resume scanning** to allow administrative access to router
- **Real-time statistics** including device counts and connection status

### Performance & Reliability

- **Adaptive polling intervals** - automatically adjusts based on network stability
- **Intelligent caching** - reduces router load and improves responsiveness
- **Connection pooling** with retry mechanisms for better reliability
- **Graceful error handling** with automatic recovery

### Modern Home Assistant Integration

- **Config Flow support** - easy setup through the UI
- **Device Registry integration** - proper device tracking with unique identifiers
- **DataUpdateCoordinator** - efficient data management following HA best practices
- **Backward compatibility** - supports existing YAML configurations with deprecation warnings

## 🔧 Compatible Routers

| Router Model  | Model Parameter | Verified |
| ------------- | :-------------: | :------: |
| ZTE F6640     |      F6640      |    ✅    |
| ZTE F6645P    |     F6645P      |    ✅    |
| ZTE H169A     |      H169A      |    ✅    |
| ZTE H2640     |      H2640      |    ✅    |
| ZTE H288A     |      H288A      |    ✅    |
| ZTE H388X     |      H388X      |    ✅    |
| ZTE H3600P    |     H3600P      |    ✅    |
| ZTE H3640 V10 |      H3640      |    ✅    |
| ZTE H6645P V2 |     H6645P      |    ✅    |
| ZTE BE5100    |      BE5100     |    ✅    |

> **Note**: This integration may work with additional ZTE router models. Try one of the above parameter values to test compatibility.
> 
> **Chinese Models**: For Chinese ZTE router models (like BE5100), use `root` as the username instead of `admin`.

## 🚀 Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Search for "ZTE Tracker"
4. Click "Download"
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/juacas/zte_tracker/releases)
2. Extract the `zte_tracker` folder to your `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

### UI Configuration (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "ZTE Tracker"
4. Enter your router details:
   - **Host**: Router IP address (usually `192.168.1.1` or `192.168.0.1`)
   - **Username**: Router admin username (usually `admin`, or `root` for Chinese models)
   - **Password**: Router admin password
   - **Model**: Select your router model from the dropdown

### Legacy YAML Configuration (Deprecated)

```yaml
# This method is deprecated - please use UI configuration instead
zte_tracker:
  host: 192.168.1.1
  model: F6640
  username: admin
  password: !secret zte_password
```

## 📊 Entities Created

### Sensors

- **Router Status Sensor** (`sensor.zte_router_[ip]`)

  - State: `on`, `paused`, or `unavailable`
  - Attributes: device list, scanning status, router info

- **Device Count Sensor** (`sensor.zte_router_[ip]_connected_devices`)
  - State: Number of connected devices
  - Unit: devices

### Device Trackers

- **Individual Device Trackers** (`device_tracker.zte_[mac_address]`)
  - State: `home` or `not_home`
  - Attributes: IP address, hostname, network type, device icon

## 🎯 Services

### `zte_tracker.reboot`

Remotely reboots the router (when supported by the router model, currently unimplemented).

```yaml
service: zte_tracker.reboot
```

### `zte_tracker.remove_tracked_entity`

Removes a tracked device entity by MAC address.

**Service data schema:**

- `mac` (string, required): MAC address of the device to remove. Example: `E4:BC:AA:0D:B8:F6`

**Example usage:**

```yaml
service: zte_tracker.remove_tracked_entity
data:
  mac: E4:BC:AA:0D:B8:F6
```

## 🕹️ Pause/Resume Tracker

To pause or resume the tracker, use the ZTE Tracker Pause switch in the Home Assistant UI. This is useful when you need to access the router's web interface without interference.

- Entity: `switch.zte_tracker_pause`
- State: `on` (paused), `off` (running)

## 🔍 Advanced Configuration

### Adaptive Polling

The integration automatically adjusts polling intervals based on network activity:

- **Fast polling** (30s): When device states are changing frequently
- **Normal polling** (60s): Default interval for stable networks
- **Slow polling** (120s): When the network has been stable for extended periods

### Device Persistence

Devices are intelligently cached and persist across:

- Temporary network disconnections
- Router reboots
- Integration restarts
- Home Assistant restarts

This ensures your automations continue working even during brief connectivity issues.

## 🛠️ Troubleshooting

### Common Issues

**"Cannot connect to router"**

- Verify the IP address is correct
- Check that the username/password are valid
- For Chinese models (like BE5100), try using `root` instead of `admin` as username
- Ensure the router's web interface is accessible
- Try accessing the router's web interface manually first

**"Device not showing as home"**

- Check if the device is connected to WiFi or LAN
- Verify the device has an active IP address
- Wait for the next scan cycle (30-120 seconds)

**"Router becomes unresponsive"**

- Use the pause service before accessing the router's web interface
- Reduce polling frequency if the router is resource-constrained
- Consider upgrading router firmware if available

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: info
  logs:
    custom_components.zte_tracker: debug
```

## 🔄 Migration from Legacy Versions

The integration automatically detects and supports legacy YAML configurations while providing migration prompts. To migrate:

1. Remove the YAML configuration from `configuration.yaml`
2. Add the integration through the UI (Settings → Devices & Services)
3. Use the same credentials and settings

Your existing device trackers and automations will continue working without changes.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/juacas/zte_tracker.git

# Install development dependencies
pip install -r requirements_dev.txt

# Run tests
pytest custom_components/zte_tracker/tests/
```

## 🙏 Acknowledgments

- **@gselivanof** for H288A, H169A models support
- **@TrinTragula** for H388X verification
- **@kvshino** for H2640 verification
- **@dapuzz** for F6645P verification
- **@onegambler** for H3600P verification
- **@lapo** for H6645P verification
- **@309631** for H3640 verification
- **Chinese ZTE community** for BE5100 verification and username guidance

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [GitHub Repository](https://github.com/juacas/zte_tracker)
- [Home Assistant Community](https://community.home-assistant.io/)
- [Issue Tracker](https://github.com/juacas/zte_tracker/issues)
- [Latest Release](https://github.com/juacas/zte_tracker/releases/latest)
