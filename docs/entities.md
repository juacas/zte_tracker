# Entities and attributes

Entity ids come from the entity name, so the router IP appears with underscores (`192.168.1.1` becomes `192_168_1_1`). Check the real ids in **Settings -> Devices & Services -> ZTE Tracker**.

| Platform | Entity | Name / id pattern |
|----------|--------|-------------------|
| `sensor` | Router status | `sensor.zte_router_<ip>` |
| `sensor` | Connected devices | `sensor.zte_router_<ip>_connected_devices` |
| `sensor` | Cellular metrics (CPE models such as G5B) | `sensor.zte_router_<ip>_<metric>`, see [Cellular sensors](#cellular-sensors) |
| `device_tracker` | One per device | Named after the device hostname, for example `device_tracker.phone`. The unique id is the MAC address |
| `switch` | Pause | `switch.zte_tracker_pause` |
| `switch` | Register new devices | `switch.zte_register_new_devices` |
| `switch` | Parental control, F680 only | One per router rule, named `<rule> Parental Control` |
| `button` | Reboot | `button.zte_router_<ip>_reboot` |

## Router status sensor

State: `connected`, `paused` (scanning paused with the Pause switch) or `unavailable` (router unreachable).

Always present: `host`, `model`, `status`, `last_update`, `poll_interval` (seconds). `total_devices` and `active_devices` are present while the state is `connected`.

What else is there depends on the model and on the **Query WAN status** and **Query router details** options (see [Configuration](configuration.md#options)).

### Router details

`ManuFacturer`, `ModelName`, `HardwareVer`, `SoftwareVer`, uptime (`PowerOnTime`), CPU usage (`CpuUsage1` to `CpuUsage4`) and memory usage (`MemUsage`). The G5B reports no CPU or memory values.

### WAN

| Attribute | Meaning |
|-----------|---------|
| `WAN_connected` | Internet link is up |
| `WAN_public_ip`, `WAN_ipv6_ip`, `WAN_gateway`, `WAN_subnet_mask`, `WAN_dns_servers` | Addressing, when the router reports it |
| `WAN_mode`, `WAN_uptime`, `WAN_remain_leasetime`, `WAN_error_message` | Connection mode, uptime, DHCP lease time left, last error |
| `WAN_rx_bytes`, `WAN_tx_bytes` | Traffic counters (G5B, F8748) |
| `WAN_rx_throughput_bps`, `WAN_tx_throughput_bps` | Current throughput (G5B) |
| `WAN_rx_packets`, `WAN_tx_packets`, `WAN_rx_errors`, `WAN_tx_errors` | Traffic counters (F8748) |
| `WAN_status_error` | Only present when the WAN query failed: the error text |

### DSL line

VDSL/ADSL models such as the H2640 report these instead of the Ethernet WAN attributes, because DSL sync is not Internet reachability: `DSL_line_status`, `DSL_upstream_rate_kbps`, `DSL_downstream_rate_kbps`, `DSL_upstream_max_rate_kbps`, `DSL_downstream_max_rate_kbps`, `DSL_upstream_noise_margin`, `DSL_downstream_noise_margin`, `DSL_upstream_attenuation`, `DSL_downstream_attenuation`, `DSL_profile`, `DSL_encapsulation`.

### GPON optical (F6600P, F6745Q)

`PON_rx_power_dbm`, `PON_tx_power_dbm`, `PON_temperature_c`, `PON_loss_of_signal`, `PON_registration_status`.

## Connected devices sensor

State: number of devices that are active now. Attributes: `num_devices` (the same number) and `devices`, a list of every known device as `MAC(name-ip)`.

## Cellular sensors

Created only for models with cellular metrics (currently G5B). A value is `unknown` until the router reports it.

| Sensor | Unit | Extra attributes |
|--------|------|------------------|
| Cellular Network Type (`ENDC`, `SA`, `LTE`, ...) | | `cellular_operator`, `cellular_plmn`, `cellular_roaming`, `cellular_ca_status`, `cellular_signal_bars` |
| Cellular Signal Bars (0 to 5) | | |
| LTE Band | | `lte_cell_id`, `lte_cell_id_hex`, `lte_pci`, `lte_earfcn`, `lte_bandwidth`, `cellular_ca_status`, `lte_ca_scell_info`, `lte_cells` (primary and secondary component carriers from *System -> Device Information*) |
| LTE RSRP, LTE RSSI | dBm | |
| LTE RSRQ, LTE SINR | dB | |
| 5G NR Band | | `nr5g_cell_id`, `nr5g_cell_id_hex`, `nr5g_pci`, `nr5g_arfcn`, `nr5g_bandwidth`, `nr5g_cells` (5G PCC and SCC carriers) |
| 5G NR RSRP, 5G NR RSSI | dBm | |
| 5G NR RSRQ, 5G NR SINR | dB | |

The router status sensor also carries `cellular_network_type`.

## Device trackers

State: `home` or `not_home`.

| Attribute | Meaning |
|-----------|---------|
| `ip_address`, `hostname`, `mac_address` | Identity. Home Assistant adds `ip`, `host_name` and `mac` with the same values |
| `network_type` | `WLAN` or `LAN` |
| `port` | SSID name or LAN port |
| `icon_type` | Device type reported by the router |
| `last_seen` | Last time the router listed the device as active |
| `link_time`, `connect_time` | Link duration and connect time from the router |
| `mesh_node` | Mesh node the device connects through, see [Mesh topology](configuration.md#mesh-topology) |

Known devices stay in the entity registry, so after a Home Assistant restart or a router reboot they come back as `not_home` until the router lists them again. Remove one for good with [`zte_tracker.remove_tracked_entity`](services.md#zte_trackerremove_tracked_entity).
