# Troubleshooting

## Common issues

**Cannot connect to the router**

- Check the IP address, username and password.
- Open the router web interface in a browser first to confirm it is reachable.

**A device does not show as `home`**

- Check that it is connected by WiFi or LAN and has an IP address.
- Wait for the next poll. The interval depends on the [Poll interval option](configuration.md#polling): 30 to 120 s by default, 10 to 300 s depending on the preset.
- For a faster result turn on [Refresh on join](configuration.md#refresh-on-join).
- Devices added while **Register new devices** is off are not created. Turn the switch on.

**The router becomes unresponsive or logs you out of its web UI**

- Turn on the Pause switch before using the router web interface.
- Use a slower Poll interval preset.
- Try **Reuse session across polls** in the options.

**My model is not listed, or a device list is empty**

Export a [support bundle](services.md#zte_trackerexport_support_bundle) and open a [new model issue](https://github.com/juacas/zte_tracker/issues/new/choose). See also [Reverse-engineering](reverse-engineering.md).

## Debug logging

```yaml
logger:
  default: warning
  logs:
    custom_components.zte_tracker: debug
    custom_components.zte_tracker.zteclient.zte_client: debug
```

Check in this order: can the integration log in, then can it fetch the device lists. Remove hostnames and MAC addresses before sharing a log.

## Sample debug log

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
