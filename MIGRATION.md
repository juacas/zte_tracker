# Migrating from the YAML version

Versions before the UI setup (v2.0.0) were configured in `configuration.yaml`. A leftover `zte_tracker:` block does not set anything up, and old option keys can make Home Assistant report an invalid configuration, so nothing is migrated automatically: remove the block and set the integration up again in the UI.

1. Remove the `zte_tracker:` block (and any `device_tracker: - platform: zte_tracker` entry) from `configuration.yaml`.
2. Restart Home Assistant.
3. Add the integration: **Settings -> Devices & Services -> Add Integration -> ZTE Tracker**, with the same host, username, password and model.
4. Check the new entity ids in **Settings -> Devices & Services -> ZTE Tracker** and update automations and dashboards that used the old ones. Examples (router `192.168.1.1`): `sensor.zte_router_192_168_1_1`, `sensor.zte_router_192_168_1_1_connected_devices`, `button.zte_router_192_168_1_1_reboot`. Device trackers are named after the device hostname, for example `device_tracker.phone`.

## Old YAML options

| Old option | Now |
|------------|-----|
| `interval_seconds`, `poll_time` | Adaptive **Poll interval** presets (a fixed interval cannot be set), see [Configuration](https://github.com/juacas/zte_tracker/blob/master/docs/configuration.md#polling) |
| `new_device_defaults: track_new_devices` | **ZTE Register New Devices** switch (`switch.zte_register_new_devices`) |
| `consider_home` | No longer an integration option |
| `zte_tracker.pause` service | **ZTE Tracker Pause** switch (`switch.zte_tracker_pause`) |

Problems after migrating: see [Troubleshooting](https://github.com/juacas/zte_tracker/blob/master/docs/troubleshooting.md) or open an [issue](https://github.com/juacas/zte_tracker/issues).
