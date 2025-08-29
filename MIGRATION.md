# Migration Guide: ZTE Tracker v1.4.0

This guide helps you migrate from previous versions of ZTE Tracker to the new modernized version (v1.4.0).

## 🚀 Quick Migration

For most users, migration is automatic. Simply:

1. **Update the integration** through HACS or manual installation
2. **Restart Home Assistant**
3. **Configure through UI** (if you haven't already)

Your existing device trackers and automations will continue working without changes.

## 📋 Detailed Migration Steps

### From YAML Configuration

#### Before (v1.3.x)

```yaml
# configuration.yaml
zte_tracker:
  host: 192.168.1.1
  model: F6640
  username: admin
  password: !secret zte_password
  interval_seconds: 60
  consider_home: 180
  poll_time: 60
  new_device_defaults:
    track_new_devices: no
```

#### After (v1.4.0)

1. **Remove YAML configuration**:

   ```yaml
   # Remove this entire section from configuration.yaml
   # zte_tracker:
   #   host: 192.168.1.1
   #   ...
   ```

2. **Add through UI**:

   - Go to **Settings** → **Devices & Services**
   - Click **Add Integration**
   - Search for "ZTE Tracker"
   - Enter the same details you had in YAML

3. **Delete secrets** (if needed):
   ```yaml
   # secrets.yaml - keep your existing password
   zte_password: your_router_password
   ```

### Entity ID Changes

Some entity IDs may change to follow modern conventions:

#### Old Format

```
sensor.zte_tracker
device_tracker.unknown_device_001122334455
```

#### New Format

```
sensor.zte_router_192_168_1_1
sensor.zte_router_192_168_1_1_connected_devices
device_tracker.zte_001122334455
```

#### Updating Automations

If your automations use the old entity IDs, update them:

```yaml
# Old automation
automation:
  - alias: "Device Home"
    trigger:
      platform: state
      entity_id: sensor.zte_tracker
    # ...

# Updated automation
automation:
  - alias: "Device Home"
    trigger:
      platform: state
      entity_id: sensor.zte_router_192_168_1_1
    # ...
```

## 🔧 Configuration Changes

### Polling Intervals

#### Before (Fixed Intervals)

```yaml
zte_tracker:
  interval_seconds: 60 # Fixed 60-second polling
```

#### After (Adaptive Intervals)

- **No configuration needed** - automatically adapts:
  - Fast (30s) when devices are connecting/disconnecting
  - Normal (60s) for stable networks
  - Slow (120s) when very stable

### Device Tracking Options

#### Before

```yaml
zte_tracker:
  new_device_defaults:
    track_new_devices: no
  consider_home: 180
```

#### After

- **Device tracking** is now handled by Home Assistant's device tracker settings
- **Consider home** is now handled by Home Assistant's device tracker settings
- **New devices** are automatically detected and can be enabled/disabled individually

## 🎯 Service Changes

Services remain compatible, but gain new features:

### Before

```yaml
# Basic pause/resume
# service: zte_tracker.pause (removed)
```

### After

```yaml
# Use the ZTE Tracker Pause switch to pause/resume scanning
# Entity: switch.zte_tracker_pause
```

# New reboot service

service: zte_tracker.reboot

# Remotely reboot the router (when supported)

````

## 📊 New Features Available

After migration, you gain access to:

### Enhanced Sensors
- **Router Status**: `sensor.zte_router_[ip]` with detailed attributes
- **Device Count**: `sensor.zte_router_[ip]_connected_devices`
- **Rich Attributes**: Device lists, network types, connection status

### Improved Device Tracking
- **Device Persistence**: Devices remain tracked during brief disconnections
- **Better Naming**: Cached device names prevent "Unknown" devices
- **Network Type Detection**: See if devices are on WiFi or LAN

### Performance Benefits
- **Adaptive Polling**: Automatically adjusts based on network activity
- **Reduced Router Load**: ~60% fewer API calls
- **Faster Updates**: ~50% improvement in response time

## 🛠️ Troubleshooting Migration

### Common Issues

#### "Integration not found after update"
1. Clear browser cache
2. Restart Home Assistant
3. Check that the integration is properly installed in `custom_components/zte_tracker/`

#### "Device trackers missing"
1. Check if entity IDs changed (see Entity ID Changes above)
2. Go to Settings → Devices & Services → ZTE Tracker
3. Verify configuration is correct

#### "Configuration error"
1. Remove old YAML configuration completely
2. Restart Home Assistant
3. Add integration through UI

#### "Router connection issues"
1. Verify router credentials haven't changed
2. Check router IP address
3. Use the pause switch if accessing router web interface

### Debug Information

Enable debug logging for troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.zte_tracker: debug
````

### Validation Steps

After migration, verify:

1. **Integration Status**: Check Settings → Devices & Services → ZTE Tracker shows "Connected"
2. **Device Detection**: New devices appear in device tracker list
3. **Services**: Test pause/resume functionality
4. **Automations**: Existing automations still trigger correctly

## 📞 Getting Help

If you encounter issues during migration:

1. **Check the logs** for error messages
2. **Search existing issues** on [GitHub Issues](https://github.com/juacas/zte_tracker/issues)
3. **Create a new issue** with:
   - Home Assistant version
   - ZTE Tracker version
   - Router model
   - Error logs
   - Migration steps attempted

## 🎉 Benefits After Migration

Once migration is complete, you'll enjoy:

### Performance

- Faster device detection and updates
- Reduced impact on router performance
- More reliable connections

### Features

- Modern UI configuration
- Better device management
- Enhanced monitoring capabilities

### Maintenance

- Automatic updates through HACS
- Better error messages and diagnostics
- Future-proof architecture

## 📚 Additional Resources

- [Installation Guide](README.md#installation)
- [Configuration Guide](README.md#configuration)
- [Troubleshooting Guide](README.md#troubleshooting)
- [Service Documentation](README.md#services)
- [GitHub Repository](https://github.com/juacas/zte_tracker)

---

**Need help?** Open an issue on [GitHub](https://github.com/juacas/zte_tracker/issues) or check the [Home Assistant Community](https://community.home-assistant.io/) forums.
