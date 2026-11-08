# Services

## `zte_tracker.reboot`

Reboots the router (supported by most models). Without `host` it reboots every configured router, `host` limits it to one.

```yaml
service: zte_tracker.reboot
```

## `zte_tracker.refresh`

Polls the router now instead of waiting for the next interval. Without `host` it polls every configured router, `host` limits it to one. Calls are rate limited to one poll every 10 seconds.

```yaml
service: zte_tracker.refresh
```

## `zte_tracker.remove_tracked_entity`

Removes a tracked device entity by MAC address. The device is removed too when no other entity is left on it.

| Field | Required | Example |
|-------|----------|---------|
| `mac` | yes | `E4:BC:AA:0D:B8:F6` |

```yaml
service: zte_tracker.remove_tracked_entity
data:
  mac: E4:BC:AA:0D:B8:F6
```

## `zte_tracker.remove_unidentified_entities`

Removes every `device_tracker` entity in the registry that has no unique ID, for any integration, not only ZTE Tracker. No fields.

## `zte_tracker.export_support_bundle`

Writes a JSON file into `zte_tracker_support/` describing the **structure** of your router's responses, for attaching to a "please support my model" issue. A failed login still produces one. Owner readable only, pruned after 24 hours.

```yaml
action: zte_tracker.export_support_bundle
data:
  acknowledge_sensitive_data: true   # required
  host: 192.168.1.1                  # optional, one router instead of all
```

| Summary field | Meaning |
|---------------|---------|
| `best_matching_profile` | The profile your router answered. Usually supportable as an alias of it |
| `tied_profiles` | Profiles sharing every endpoint, so probing cannot separate them |
| `nodes_not_understood` | Data your firmware returns that no parser reads yet |
| `endpoints_answered_empty` | Endpoints that exist and returned no devices |

> [!NOTE]
> No hostname, SSID, serial, MAC or IP address is collected: only node and field names, record counts, and the shape of each value. Names come from your firmware, so have a look before attaching it.
