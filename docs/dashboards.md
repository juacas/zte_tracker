# Dashboard examples

Both need the [auto-entities](https://github.com/thomasloven/lovelace-auto-entities) card. The second one also needs [flex-table-card](https://github.com/custom-cards/flex-table-card). These examples are not tested against every setup, adjust them to yours.

## All tracked devices

```yaml
type: custom:auto-entities
filter:
  include:
    - domain: device_tracker
      integration: zte_tracker
sort:
  method: name
card:
  type: entities
  title: ZTE Connected Devices
```

## Table of devices that are home

```yaml
type: custom:auto-entities
filter:
  include:
    - domain: device_tracker
      integration: zte_tracker
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

The columns are device tracker attributes, see [Entities](entities.md#device-trackers).
