![GitHub](https://img.shields.io/github/license/juacas/zte_tracker)
![GitHub Repo stars](https://img.shields.io/github/stars/juacas/zte_tracker)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/juacas/zte_tracker)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate with hassfest](https://github.com/juacas/zte_tracker/actions/workflows/hassfest.yml/badge.svg?branch=master)](https://github.com/juacas/zte_tracker/actions/workflows/hassfest.yml)
[![Validate with HACS](https://github.com/juacas/zte_tracker/actions/workflows/hacsaction.yml/badge.svg)](https://github.com/juacas/zte_tracker/actions/workflows/hacsaction.yml)


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

- **Router status monitoring** with connection health indicators: WAN uptime, WAN_remain_leasetime, WAN_error_message, WAN_connected (kindly requested by @cagnulein)
- **Remote router reboot** capability through service calls (**Now implemented!**)
- **Pause/resume scanning** to allow administrative access to router from other browsers
- **Real-time statistics** including device counts and connection status
- **Router details available as sensor attributes** (model, firmware, uptime, WAN info, etc.)

### Performance & Reliability

- **Adaptive polling intervals** - automatically adjusts based on network stability
- **Intelligent caching** - reduces router load and improves responsiveness
- **Connection pooling** with retry mechanisms for better reliability
- **Graceful error handling** with automatic recovery

### Modern Home Assistant Integration

- **Config Flow support** - easy setup through the UI
- **Device Registry integration** - proper device tracking with unique identifiers
- **DataUpdateCoordinator** - efficient data management following HA best practices
- **Backward compatibility** - need to remove legacy YAML configuration
- **HACS support** - easy installation and updates via Home Assistant Community Store

## 📊 Entities Created

### Sensors

- **Router Status Sensor** (`sensor.zte_router_[ip]`)

  - State: `on`, `paused`, or `unavailable`
  - Attributes:
    - device list
    - scanning status
    - last update time
    - WAN uptime
    - WAN_remain_leasetime
    - WAN_error_message
    - WAN_connected
    - **Router details**: model, firmware version, uptime, MAC address, IP address, Memory usage, CPU usage, etc.

- **Device Count Sensor** (`sensor.zte_router_[ip]_connected_devices`)
  - State: Number of connected devices
  - Attributes: list of devices detected.

### Device Trackers

- **Individual Device Trackers** (`device_tracker.zte_[mac_address]`)
  - State: `home` or `not_home`
  - Attributes: IP address, hostname, network type (WLAN/LAN), device icon, last seen time, port (SSID name or LAN port), link duration, connect time.

## 🎯 Services

### `zte_tracker.reboot`

Remotely reboots the router (supported by most router models).

**Example usage:**

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

## 🧩 Register New Devices

To control whether newly discovered devices are added as `device_tracker` entities, use the ZTE Register New Devices switch.

- Entity: `switch.zte_register_new_devices`
- State: `on` (new devices will be registered), `off` (only existing tracked devices are updated)

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
| ZTE AX3000    |      AX3000    |    ✅    |
| ZTE SR7410 (ZTE BE7200 Pro+)   |      SR7410      |    ✅    |

> **Note**: This integration may work with additional ZTE router models. Try one of the above parameter values to test compatibility.

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
   - **Username**: Router admin username (usually `admin`)
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
## Add to your dashboard

### With auto-entities card
To automatically display all connected devices on your dashboard, you can use the [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) card.

```yaml
type: custom:auto-entities
filter:
  include:
    - entity_id: device_tracker.zte_*
sort: name
card:
  type: entities
  title: ZTE Connected Devices
```

### Display with auto-entities card and flex-table card

```yaml
type: custom:auto-entities
filter:
  include:
    - options: {}
      domain: device_tracker
      state: home
card:
  type: custom:flex-table-card
  title: ZTE-Tracked Devices
  clickable: true
  sort_by: connect_time
  columns:
    - data: icon
      name: Type
    - data: network_type
      name: Net
    - data: state
      name: State
    - data: host_name
      name: Host
    - data: mac
      name: MAC
    - data: port
      name: At
    - data: last_seen
      name: Seen
      fmt: hours_mins_passed
    - data: connect_time
      name: Conn
```

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

- **@juacas** for original development and ongoing maintenance
- **@gselivanof** for H288A, H169A models support
- **@TrinTragula** for H388X verification
- **@kvshino** for H2640 verification
- **@dapuzz** for F6645P verification
- **@onegambler** for H3600P verification
- **@lapo** for H6645P verification
- **@309631** for H3640 verification
- **@LZDEROH** for AX3000 verification
- **gradypark86** for SR7410 verification

## 📄 License

This project is licensed under the GNU License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [GitHub Repository](https://github.com/juacas/zte_tracker)
- [Home Assistant Community](https://community.home-assistant.io/)
- [Issue Tracker](https://github.com/juacas/zte_tracker/issues)
- [Latest Release](https://github.com/juacas/zte_tracker/releases/latest)

## 🕵️‍♂️ Reverse-Engineering the Router Web Console

If your ZTE router model is not listed above or you want to extend integration support, you can reverse-engineer the router's web console to discover how it exposes device and status information.

### Steps to Reverse-Engineer

1. **Access the Router Web Console**
   Open your browser and log in to your router's web interface (usually at `http://192.168.1.1`).

2. **Open Developer Tools**
   Press <kbd>F12</kbd> or right-click and select "Inspect" to open your browser's developer tools.

3. **Monitor Network Requests**
   Go to the "Network" tab and look for requests made when you view device lists, status pages, or perform actions (like reboot).

4. **Identify API Endpoints**
   Filter by `XHR` or `Fetch` requests. Look for URLs ending in `.lua`, `.cgi`, or similar, and inspect the request/response payloads.

5. **Analyze Data Formats**
   ZTE routers typically return data in XML or JSON. Copy the response and note the structure—especially device lists, status fields, and control commands.

6. **Test Requests Manually**
   Use tools like Developer Tools (Replay XHR), [Postman](https://www.postman.com/) or `curl` to replicate requests outside the browser.
   Example:

   ```bash
   curl -k "https://192.168.1.1/?_type=menuData&_tag=wlan_client_stat_lua.lua"
   ```

7. **Document Parameters**
   Note required headers, authentication methods, and any session tokens.

8. **Map Data to Integration**
   Match fields like MAC address, IP, hostname, connection type, and status to the integration's expected format.

9. **Check Login Mechanism**
   To be sure that current login implementation is valid, enable debug for the integration and look for login errors.
   To enable debug, edit `configuration.yaml` and set `logger` to `debug` level for the integration by adding:

```yaml
logger:
  default: warning
  logs:
    custom_components.zte_tracker: debug
    custom_components.zte_tracker.zteclient.zte_client: debug
```

For login-related errors or warnings, enable and inspect debug logs as described in the "Before reverse-engineering understand and check debug logs" section: [Before reverse-engineering understand and check debug logs](#before-reverse-engineering-understand-and-check-debug-logs)

### Example: Sequences of URLs

Below are the actual URL sequences used by the integration for the most common ZTE router models:

#### **F6640 / F6645P**

- **Login Sequence:**

  1. `GET  https://[router_ip]/?_type=loginData&_tag=login_entry`
  2. `GET  https://[router_ip]/?_type=loginData&_tag=login_token&_=[guid]`
  3. `POST https://[router_ip]/?_type=loginData&_tag=login_entry` (with hashed password and session token)

- **Get WiFi Devices:**

  1. `GET  https://[router_ip]/?_type=menuView&_tag=localNetStatus&_=[guid]`
  2. `GET  https://[router_ip]/?_type=menuData&_tag=wlan_client_stat_lua.lua&_=[guid]`

- **Get LAN Devices:**

  1. `GET  https://[router_ip]/?_type=menuView&_tag=localNetStatus&_=[guid]`
  2. `GET  https://[router_ip]/?_type=menuData&_tag=accessdev_landevs_lua.lua&_=[guid]`

- **Get Router Details:**

  1. `GET  https://[router_ip]/?_type=menuView&_tag=statusMgr&Menu3Location=0&_=[guid]`
  2. `GET  https://[router_ip]/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_=[guid]`

- **Get WAN Status:**

  1. `GET  https://[router_ip]/?_type=menuView&_tag=ethWanStatus&Menu3Location=0&_=[guid]`
  2. `GET  https://[router_ip]/?_type=menuData&_tag=wan_internetstatus_lua.lua&TypeUplink=2&pageType=1&_=[guid]`

- **Reboot Router:**
  1. `GET  https://[router_ip]/?_type=menuView&_tag=rebootAndReset&Menu3Location=0&_=[guid]`
  2. `POST https://[router_ip]/?_type=menuData&_tag=devmgr_restartmgr_lua.lua&_=[guid]` (with encrypted digest and session token)

#### **H288A / H169A / H388X / H2640 / H3600P / H6645P / H3640**

- **WiFi Devices:**
  `GET https://[router_ip]/?_type=menuData&_tag=accessdev_ssiddev_lua.lua&_=[guid]`
- **LAN Devices:**
  `GET https://[router_ip]/?_type=menuData&_tag=accessdev_landevs_lua.lua&_=[guid]`

#### **E2631**

- **WiFi Devices:**
  `GET https://[router_ip]/?_type=vueData&_tag=vue_client_data&_=[guid]`
- **LAN Devices:**
  `GET https://[router_ip]/?_type=vueData&_tag=localnet_lan_info_lua&_=[guid]`

> Replace `[router_ip]` with your router's IP (e.g., `192.168.1.1`).
> `[guid]` is a unique number generated for each request.

### Example XML Response (F6640 Device List)

```xml
<ajax_response_xml_root>
  <OBJ_WLAN_AD_ID>
    <Instance>
      <ParaName>MACAddress</ParaName>
      <ParaValue>58:e4:03:f2:7b:f2</ParaValue>
      ...
    </Instance>
    ...
  </OBJ_WLAN_AD_ID>
</ajax_response_xml_root>
```

<a id="before-reverse-engineering-understand-and-check-debug-logs"></a>

### Before reverse-engineering understand and check debug logs

Before begining to reverse engineering check what extent id zte_tracker working with your router.
First, check is it is able to login into the router.
Second, check if it is able to retrieve device lists.

To enable debug logging for the integration, edit `configuration.yaml` and set `logger` to `debug` level for the integration by adding:

```yaml
logger:
  default: warning
  logs:
    custom_components.zte_tracker: debug
    custom_components.zte_tracker.zteclient.zte_client: debug
```

Look for any errors or warnings related to login attempts. Example:

Typical successful login sequence:
```
2025-09-01 08:27:18.699 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=loginData&_tag=login_entry Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:18.873 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=loginData&_tag=login_token&_=[guid] Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:19.053 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=loginData&_tag=login_entry Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:19.054 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Login refresh required
```

Typical successful retrieval of devices:
```
2025-09-01 08:27:19.294 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuView&_tag=localNetStatus&_=GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:19.507 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuData&_tag=accessdev_landevs_lua.lua&_GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:19.507 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Found 21 device instances in XML
2025-09-01 08:27:19.508 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Parsed 21 valid devices
2025-09-01 08:27:19.782 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuData&_tag=wlan_client_stat_lua.lua&_=GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:19.784 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Found 18 device instances in XML
2025-09-01 08:27:19.784 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Parsed 18 valid devices
2025-09-01 08:27:20.209 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuData&_tag=wan_internetstatus_lua.lua&TypeUplink=2&pageType=1&_=GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:20.435 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuView&_tag=statusMgr&Menu3Location=0&_=GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:20.645 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_=GUID Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
```
Typical successful logout sequence:
```
2025-09-01 08:27:20.852 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Request 200 URL: https://ROUTER_IP/?_type=loginData&_tag=logout_entry Headers: {..., 'Cookie': 'SID_HTTPS_=ANON_COOKIE'}
2025-09-01 08:27:20.852 DEBUG (SyncWorker_1) [custom_components.zte_tracker.zteclient.zte_client] Logged out successfully
2025-09-01 08:27:20.854 DEBUG (MainThread) [custom_components.zte_tracker.coordinator] Adjusting update interval from 0:00:30 to 0:01:00 (stable count: 2)
2025-09-01 08:27:20.854 DEBUG (MainThread) [custom_components.zte_tracker.coordinator] Finished fetching zte_tracker data in 2.355 seconds (success: True)
2025-09-01 08:27:33.690 INFO (MainThread) [custom_components.zte_tracker] No unidentified device_tracker entities found to remove.
```
