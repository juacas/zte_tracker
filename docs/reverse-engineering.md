# Reverse-engineering a router

Use this when your model is not in the [supported list](https://github.com/juacas/zte_tracker#supported-routers), or to extend support. Start with the [support bundle](services.md#zte_trackerexport_support_bundle): it often shows that your router is just an alias of a known profile. Then check what the integration already does in the [debug logs](troubleshooting.md#debug-logging).

## Steps

1. **Access the Router Web Console**
   Open your browser and log in to your router's web interface (usually at `http://192.168.1.1`).

2. **Open Developer Tools**
   Press <kbd>F12</kbd> or right-click and select "Inspect" to open your browser's developer tools.

3. **Monitor Network Requests**
   Go to the "Network" tab and look for requests made when you view device lists, status pages, or perform actions (like reboot).

4. **Identify API Endpoints**
   Filter by `XHR` or `Fetch` requests. Look for URLs ending in `.lua`, `.cgi`, or similar, and inspect the request/response payloads.

5. **Analyze Data Formats**
   ZTE routers typically return data in XML or JSON. Copy the response and note the structure, especially device lists, status fields, and control commands.

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

9. **Check the login**
   Enable [debug logging](troubleshooting.md#debug-logging) and compare the login requests with the [sample log](troubleshooting.md#sample-debug-log).

## URL sequences

Below are the actual URL sequences used by the integration for the most common ZTE router models:

### F6640 / F6645P

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

### H288A / H169A / H168A / H388X / H2640 / H3600P / H6645P / H3640

- **WiFi Devices:**
  `GET https://[router_ip]/?_type=menuData&_tag=accessdev_ssiddev_lua.lua&_=[guid]`
- **LAN Devices:**
  `GET https://[router_ip]/?_type=menuData&_tag=accessdev_landevs_lua.lua&_=[guid]`

### E2631

- **WiFi Devices:**
  `GET https://[router_ip]/?_type=vueData&_tag=vue_client_data&_=[guid]`
- **LAN Devices:**
  `GET https://[router_ip]/?_type=vueData&_tag=localnet_lan_info_lua&_=[guid]`

> Replace `[router_ip]` with your router's IP (e.g., `192.168.1.1`).
> `[guid]` is a unique number generated for each request.

## Example XML response (F6640 device list)

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

## G5B (JSON goform API)

The G5B 5G CPE does not use the Lua/XML `menuData` tags. It answers JSON on `/goform/goform_get_cmd_process` (reads) and `/goform/goform_set_cmd_process` (login, reboot). The Network tab of the browser shows the `cmd=` values the page asks for.
