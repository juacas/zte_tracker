![GitHub](https://img.shields.io/github/license/juacas/zte_tracker)
![GitHub Repo stars](https://img.shields.io/github/stars/juacas/zte_tracker)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/juacas/zte_tracker)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate with hassfest](https://github.com/juacas/zte_tracker/actions/workflows/hassfest.yml/badge.svg?branch=master)](https://github.com/juacas/zte_tracker/actions/workflows/hassfest.yml)
[![Validate with HACS](https://github.com/juacas/zte_tracker/actions/workflows/hacsaction.yml/badge.svg)](https://github.com/juacas/zte_tracker/actions/workflows/hacsaction.yml)
[![Tests](https://github.com/juacas/zte_tracker/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/juacas/zte_tracker/actions/workflows/tests.yml)


![GitHub contributors](https://img.shields.io/github/contributors/juacas/zte_tracker)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/juacas/zte_tracker)
![GitHub commits since tagged version](https://img.shields.io/github/commits-since/juacas/zte_tracker/latest)
![GitHub last commit](https://img.shields.io/github/last-commit/juacas/zte_tracker)
![installation_badge](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.zte_tracker.total)
> [!NOTE]
> **Project stewardship**
>
> With huge generosity, [@lebdim](https://github.com/lebdim) has contributed substantially to this integration and is now in charge of the project. Please join me in thanking him and direct future maintenance and support contributions his way. The call remains open for additional maintainers and collaborators who would like to help keep the project growing.

# ZTE Router Integration for Home Assistant

Track the devices on your ZTE router and manage the router from Home Assistant.

## Features

- Presence tracking of WiFi and LAN devices, with SSID, network type and last seen time
- Mesh support: devices on controller and agent nodes, with a `mesh_node` attribute
- Known devices stay in the registry and come back after a restart, names fall back to cached ones
- Router sensors: connected devices, status, WAN, DSL and GPON details, firmware, CPU and memory, cellular signal (G5B)
- Reboot button, pause switch, register-new-devices switch, parental control switches (F680)
- Adaptive polling with presets, optional refresh the moment a device joins the network
- Support bundle and diagnostics to get a new model supported
- UI setup and options, installable with HACS

## Supported routers

| Router Model                 | Model Parameter |     Verified     |
| ---------------------------- | :-------------: | :--------------: |
| ZTE F6640                    |      F6640      |        ✅        |
| ZTE F6645P                   |     F6645P      |        ✅        |
| ZTE F680                     |      F680       |        ✅        |
| ZTE F6745Q                   |     F6745Q      |        ✅        |
| ZTE F6600P                   |     F6600P      |        ✅        |
| ZTE F8748                    |      F8748      |        ✅        |
| ZTE G5B                      |       G5B       |        ✅        |
| ZTE H168A V2.1               |      H168A      |        ✅        |
| ZTE H169A                    |      H169A      |        ✅        |
| ZTE H2640                    |      H2640      |        ✅        |
| ZTE H288A                    |      H288A      |        ✅        |
| ZTE H388X                    |      H388X      |        ✅        |
| ZTE H3600P                   |     H3600P      |        ✅        |
| ZTE H3640 V10                |      H3640      |        ✅        |
| ZTE H6645P V2                |     H6645P      |        ✅        |
| ZTE H6745 V3                 |      H6745      |        ✅        |
| ZTE AX3000                   |      E2631      |        ✅        |
| ZTE SR7110                   |     SR7110      | alias of E2631   |
| ZTE SR7410 (ZTE BE7200 Pro+) |     SR7410      |        ✅        |

**Not listed?** It may still work: try each parameter value above. If not, run [`zte_tracker.export_support_bundle`](https://github.com/juacas/zte_tracker/blob/master/docs/services.md#zte_trackerexport_support_bundle) and attach the file to a [new model issue](https://github.com/juacas/zte_tracker/issues/new/choose). More in [Reverse-engineering](https://github.com/juacas/zte_tracker/blob/master/docs/reverse-engineering.md).

**F8748**: verified on a DIGI Portugal unit (firmware `V3.0.10P2N4`). It shares the F6640 endpoints but is a separate model because this firmware also exposes WAN traffic counters (`WAN_rx_bytes`, `WAN_tx_bytes`, `WAN_rx_packets`, `WAN_tx_packets`, `WAN_rx_errors`, `WAN_tx_errors`). They are parsed only for `F8748`, other F6640-family routers are unaffected. DIGI units in other countries are likely identical, other F8748 units may expose more data we could not confirm.

## Installation

HACS (recommended): open HACS, search for **ZTE Tracker**, click **Download**, restart Home Assistant.

Manual: download the latest [release](https://github.com/juacas/zte_tracker/releases), copy the `zte_tracker` folder to `custom_components`, restart Home Assistant.

## Setup

1. **Settings -> Devices & Services -> Add Integration -> ZTE Tracker**
2. Enter **Host** (usually `192.168.1.1`), **Username** (usually `admin`), **Password** and the **Model** from the table above. The form also offers the optional extra queries and session reuse, see [Configuration](https://github.com/juacas/zte_tracker/blob/master/docs/configuration.md#options).

YAML configuration is not supported. If you still have `zte_tracker:` or a `zte_tracker` device tracker in `configuration.yaml`, remove it and add the integration as above. See [MIGRATION.md](https://github.com/juacas/zte_tracker/blob/master/MIGRATION.md).

All options (extra queries, polling, mesh, refresh on join) are in [Configuration](https://github.com/juacas/zte_tracker/blob/master/docs/configuration.md).

## Entities

| Entity | Example id |
|--------|------------|
| Router status sensor | `sensor.zte_router_192_168_1_1` |
| Connected devices sensor | `sensor.zte_router_192_168_1_1_connected_devices` |
| Cellular sensors (G5B) | `sensor.zte_router_192_168_1_1_lte_rsrp` |
| Device tracker, one per device | `device_tracker.phone` |
| Pause switch | `switch.zte_tracker_pause` |
| Register new devices switch | `switch.zte_register_new_devices` |
| Parental control switches (F680) | named `<rule> Parental Control` |
| Reboot button | `button.zte_router_192_168_1_1_reboot` |

All attributes are listed in [Entities](https://github.com/juacas/zte_tracker/blob/master/docs/entities.md). Dashboard examples are in [Dashboards](https://github.com/juacas/zte_tracker/blob/master/docs/dashboards.md).

## Services

| Service | What it does |
|---------|--------------|
| `zte_tracker.reboot` | Reboots the router (supported by most models) |
| `zte_tracker.refresh` | Polls the router now, at most once every 10 s |
| `zte_tracker.remove_tracked_entity` | Removes a device entity by MAC address |
| `zte_tracker.remove_unidentified_entities` | Removes device trackers without a unique ID |
| `zte_tracker.export_support_bundle` | Writes a structure-only JSON file of the router's responses for a support request |

Details and examples in [Services](https://github.com/juacas/zte_tracker/blob/master/docs/services.md).

## Troubleshooting

Enable debug logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.zte_tracker: debug
```

Common problems and sample logs are in [Troubleshooting](https://github.com/juacas/zte_tracker/blob/master/docs/troubleshooting.md).

## Contributing

Fork, create a branch, add tests, open a pull request. To run the tests:

```bash
git clone https://github.com/juacas/zte_tracker.git
cd zte_tracker
pip install -r tests/requirements_test.txt
python -m pytest tests/
```

## Acknowledgments

- **@juacas** for original development and ongoing maintenance
- **@lebdim** for major contributions and project stewardship from v2.1.0 upwards
- **@cagnulein** for requesting the WAN status attributes
- **@Ices-Eyes** for fixing unconnected devices issue #72
- **@gselivanof** for H288A, H169A models support
- **@TrinTragula** for H388X verification
- **@kvshino** for H2640 verification
- **@dapuzz** for F6645P verification
- **@onegambler** for H3600P verification
- **@lapo** for H6645P verification
- **@309631** for H3640 verification
- **@stefanosalatini** for H6745 support bundle (#74)
- **@LZDEROH** for AX3000 verification
- **@gradypark86** for SR7410 verification
- **@LeMehdi0** for F6745Q support bundle (#106)
- **@enisyugnak** for H168A support bundle (#112)
- **@olaldiko** for G5B support (#130)

## License

GNU General Public License v3.0, see [LICENSE](https://github.com/juacas/zte_tracker/blob/master/LICENSE).

[GitHub](https://github.com/juacas/zte_tracker) | [Issues](https://github.com/juacas/zte_tracker/issues) | [Latest release](https://github.com/juacas/zte_tracker/releases/latest) | [Home Assistant Community](https://community.home-assistant.io/)
