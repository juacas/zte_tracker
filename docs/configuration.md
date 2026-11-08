# Configuration

## Options

Open **Settings -> Devices & Services -> ZTE Tracker -> Configure**.

| Option | Default | What it does |
|--------|---------|--------------|
| Router connection | from setup | Host, username and password |
| Query WAN status | on | Adds WAN details (IP, link state, uptime, optical levels on supported models) to the router status sensor. One extra request per poll |
| Query router details | on | Adds model, firmware, uptime, CPU and memory usage to the router status sensor. One extra request per poll |
| Reuse session across polls | off | Keeps the router login between polls instead of logging in and out every time (up to about 120 login/logout pairs per hour). Added for routers that occasionally answer "Client token is not equal to server token". The session is renewed every 30 minutes and re-created, with one retry, if the router drops it |
| Mesh topology | off | Also lists devices connected to mesh agent nodes, see [Mesh topology](#mesh-topology) |
| Poll interval | Adaptive balanced | See [Polling](#polling) |
| Refresh when a device joins the network | off | See [Refresh on join](#refresh-on-join) |

Turn the two query options off on models that do not support them, or to avoid extra load and warnings.

The router model cannot be changed afterwards: remove the integration and add it again.

## Polling

Each poll logs in to the router, so very short intervals can log you out of its web UI.

Every preset speeds up when the number of devices changes and slows down after more than 5 stable polls (fast, normal, slow step):

| Preset | Steps |
|--------|-------|
| Adaptive balanced (default) | 30 / 60 / 120 s |
| Adaptive fast | 10 / 30 / 60 s. Changes show up sooner, the router is polled more often |
| Adaptive relaxed | 60 / 120 / 300 s. Less load on the router |

If the router does not answer, the last known devices are kept for up to 10 minutes and the router sensor shows `unavailable`; after that devices show as away.

## Refresh on join

Turn on **Refresh when a device joins the network** to poll right after a device that the router does not list as active announces itself on the LAN. A new arrival shows up in a few seconds instead of up to a minute.

- Joins are heard as ARP frames through a Linux packet socket, so devices with a static IP are caught too.
- Home Assistant must be on the same network as the devices (not across VLANs, and not with Wi-Fi client isolation) and have raw-socket access (default on Home Assistant OS; a container needs host networking and `NET_RAW`). If the listener cannot start, a warning is logged and polling continues unchanged.
- Traffic from devices that are already active never triggers a poll. A MAC the router still does not list after two checks is ignored for an hour.
- Works anywhere instead: call [`zte_tracker.refresh`](services.md#zte_trackerrefresh) from an automation, for example when the Companion app reports a phone joined the Wi-Fi.
- A device leaving is still found by polling.

## Switches

| Switch | `on` means |
|--------|------------|
| `switch.zte_tracker_pause` | Scanning is paused and the router session is closed. Use it before opening the router web UI so the integration does not log you out |
| `switch.zte_register_new_devices` | New devices get a `device_tracker` entity. When `off`, only devices already tracked are updated |

## Parental control (F680)

On the ZTE F680, the router's existing Parental Control rules appear as switches. The integration never creates or edits rules, it only toggles the rule's `Enable` state.

- One switch per router rule, named after the rule `Name`.
- The state mirrors the router's live `Enable` value. Whether `on` allows or blocks Internet depends on how the rule is set up in the router.
- Create the rules in the router UI first, then reload the integration to pick up new ones.

## Mesh topology

For mesh setups (for example F6600P controller + H196A agent), enable **Mesh topology** in the options to see devices on every mesh node, not only on the controller.

- The full device list comes from the router's topology endpoint (`topo_lua.lua`).
- SSID names are filled in from the legacy WiFi endpoints. Devices on an agent inherit the SSID of controller devices with the same access type (band).
- Each device tracker gets a `mesh_node` attribute with the node it connects through.
- If topology is unavailable the integration falls back to the normal LAN and WiFi lists. After 3 consecutive failures topology is switched off for 5 minutes.
- Verified only on the F6640 family (F6640, F6600P). Other models may not have the endpoint.

## Support bundle and diagnostics

[`zte_tracker.export_support_bundle`](services.md#zte_trackerexport_support_bundle) writes a JSON file describing the **structure** of your router's responses, for a "please support my model" issue. Diagnostics (device page -> three dots -> Download diagnostics) is the other artifact: shapes and counts for when a **supported** router misbehaves.

## Dashboards

[Dashboard examples](dashboards.md).
