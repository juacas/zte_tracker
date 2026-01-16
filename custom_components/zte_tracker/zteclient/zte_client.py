from __future__ import annotations
import datetime
from os import error

"""ZTE router client with improved security and error handling."""

import base64
import hashlib
import logging
import time
from typing import Any
import warnings
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

# Suppress InsecureRequestWarning globally
warnings.simplefilter("ignore", InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)

_MODELS = {
    "F6640": {
        "wlan_script": "wlan_client_stat_lua.lua",
        "wlan_id_element": "OBJ_WLAN_AD_ID",
        "lan_script": "accessdev_landevs_lua.lua",
        "lan_id_element": "OBJ_ACCESSDEV_ID",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
        'tag_wan_status_view': "ethWanStatus&Menu3Location=0",
        "tag_wan_status_data": "wan_internetstatus_lua.lua&TypeUplink=2&pageType=1",
    },
    "H288A": {
        "wlan_script": "accessdev_ssiddev_lua.lua",
        "wlan_id_element": "OBJ_ACCESSDEV_ID",
        "lan_script": "accessdev_landevs_lua.lua",
        "lan_id_element": "OBJ_ACCESSDEV_ID",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
        'tag_wan_status_view': "ethWanStatus&Menu3Location=0",
        "tag_wan_status_data": "wan_internetstatus_lua.lua&TypeUplink=2&pageType=1",
    },
    "H388X": {
        "wlan_script": "accessdev_ssiddev_lua.lua",
        "wlan_id_element": "OBJ_ACCESSDEV_ID",
        "lan_script": "accessdev_landevs_lua.lua",
        "lan_id_element": "OBJ_ACCESSDEV_ID",
        "type_first_request": "menuView",
        "type_main_request": "menuData",
        'tag_wan_status_view': "ethWanStatus&Menu3Location=0",
        "tag_wan_status_data": "wan_internet_lua.lua&TypeUplink=2&pageType=1", # Reported in #44 wan_internetstatus_lua does not work on H388X
    },
    "E2631": {
        "wlan_script": "vue_client_data",
        "wlan_id_element": "OBJ_CLIENTS_ID",
        "lan_script": "localnet_lan_info_lua",
        "lan_id_element": "OBJ_LAN_INFO_ID",
        "type_first_request": "vueData",
        "type_main_request": "vueData",
        "tag_wan_status_view": "vue_home_device_data_no_update_sess",
        "tag_wan_status_data": "vue_mainwan_data",
    },
}

# Add synonyms
_MODELS["H169A"] = _MODELS["H288A"]
_MODELS["H2640"] = _MODELS["H288A"]
_MODELS["F6645P"] = _MODELS["F6640"]
_MODELS["F6600P"] = _MODELS["F6640"]
_MODELS["H3600P"] = _MODELS["H288A"]
_MODELS["H6645P"] = _MODELS["H288A"]
_MODELS["H3640"] = _MODELS["H288A"]
_MODELS["E2631"] = _MODELS["E2631"]
_MODELS["SR7410"] = _MODELS["E2631"]
_MODELS["SR7110"] = _MODELS["E2631"]


class zteClient:
    """ZTE router client with improved security and reliability."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        model: str,
        verify_ssl: bool = False,
    ) -> None:
        """Initialize the client."""
        self.statusmsg: str | None = None
        self.host = host
        self.username = username
        self.password = password
        self.session: Session | None = None
        self.login_data: dict[str, Any] | None = None
        self.status = "on"
        self.device_info: dict[str, Any] | None = None
        self.guid = int(time.time() * 1000)
        self.model = model
        self.paths = _MODELS[model]
        self.verify_ssl = verify_ssl

    @staticmethod
    def get_models() -> list[str]:
        """Return the list of supported model keys."""
        return list(_MODELS.keys())

    def _setup_session(self) -> None:
        """Set up HTTP session with retry strategy and security settings."""
        self.session = Session()

        # Set up retry strategy
        retry_strategy = Retry(
            total=0,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "DNT": "1",
            }
        )
        # self.session.cookies.set("_TESTCOOKIESUPPORT", "1")

    def login(self) -> bool:
        """Login procedure using ZTE challenge. Returns True if successful, False otherwise. Sets statusmsg for error reporting."""
        try:
            # Check if we are logged in already.
            if self.login_data is not None and self.session is not None:
                if self.login_data.get("login_need_refresh") == 0:
                    _LOGGER.debug("Already logged in, no need to refresh.")
                    return True

            self._setup_session()
            # Step1: Get session token
            try:
                session_token = self.get_session_token()
            except requests.exceptions.ConnectionError:
                self.statusmsg = f"Cannot connect to router at {self.host}. Please check network and address."
                return False
            except requests.exceptions.Timeout:
                self.statusmsg = f"Connection to router at {self.host} timed out."
                return False
            except Exception as e:
                self.statusmsg = f"Error getting session token: {e}"
                return False

            # Step2: Query for login token
            try:
                r = self.session.get(
                    f"https://{self.host}/?_type=loginData&_tag=login_token&_={self.get_guid()}",
                    verify=self.verify_ssl,
                    timeout=10,
                )
                self.log_request(r)
                r.raise_for_status()
            except requests.exceptions.ConnectionError:
                self.statusmsg = (
                    f"Cannot connect to router at {self.host} (login token)."
                )
                return False
            except requests.exceptions.Timeout:
                self.statusmsg = (
                    f"Connection to router at {self.host} timed out (login token)."
                )
                return False
            except Exception as e:
                self.statusmsg = f"Error getting login token: {e}"
                return False

            # Parse XML response
            try:
                xml_response = ET.fromstring(r.content)
                if xml_response.tag != "ajax_response_xml_root":
                    self.statusmsg = (
                        f"Unexpected response format from router: {xml_response.tag}"
                    )
                    return False
                login_token = xml_response.text
                if not login_token:
                    self.statusmsg = "Empty login_token received from router."
                    return False
            except Exception as e:
                self.statusmsg = f"Error parsing login token XML: {e}"
                return False

            # Step3: Login entry
            pass_hash = self.password + login_token
            password_param = hashlib.sha256(pass_hash.encode()).hexdigest()
            try:
                r = self.session.post(
                    f"https://{self.host}/?_type=loginData&_tag=login_entry",
                    verify=self.verify_ssl,
                    timeout=10,
                    data={
                        "action": "login",
                        "Password": password_param,
                        "Username": self.username,
                        "_sessionTOKEN": session_token,
                    },
                )
                self.log_request(r)
                r.raise_for_status()
                self.login_data = r.json()
            except requests.exceptions.ConnectionError:
                self.statusmsg = (
                    f"Cannot connect to router at {self.host} (login entry)."
                )
                return False
            except requests.exceptions.Timeout:
                self.statusmsg = (
                    f"Connection to router at {self.host} timed out (login entry)."
                )
                return False
            except Exception as e:
                self.statusmsg = f"Error during login entry: {e}"
                return False

            # Handle refresh requirement
            if self.login_data.get("login_need_refresh") == 1:
                _LOGGER.debug("Login refresh required")
            # Check for error messaging.
            if self.login_data.get("lockingTime", 0) == -1:
                self.statusmsg = f"Router is locked: {self.login_data.get('loginErrMsg', 'Unknown error')}"
                return False
            if self.login_data.get("lockingTime", 0) > 0:
                self.statusmsg = f"Router is locked for {self.login_data.get('lockingTime', 0)} seconds: Too many login errors."
                return False

            # Detect login denied due to bad username or password
            if (
                self.login_data is not None
                and "loginErrMsg" in self.login_data
                and self.login_data["loginErrMsg"]
                and "password" in self.login_data["loginErrMsg"].lower()
            ):
                self.statusmsg = f"Login denied: {self.login_data['loginErrMsg']}"
                return False

            self.statusmsg = "Login successful."
            return True
        except Exception as e:
            self.statusmsg = f"Failed login: {e}"
            _LOGGER.error(self.statusmsg)
            self.login_data = None
            if self.session:
                self.session.close()
                self.session = None
            return False

    def get_guid(self) -> int:
        """Get next GUID for requests."""
        guid = self.guid
        self.guid += 1
        return guid

    def get_session_token(self) -> str:
        """Get session token from router."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        r = self.session.get(
            f"https://{self.host}/?_type=loginData&_tag=login_entry",
            verify=self.verify_ssl,
            timeout=10,
        )
        self.log_request(r)
        r.raise_for_status()

        self.status = "on"
        device_info = r.json()

        if device_info.get("lockingTime", 1) != 0 or not device_info.get("sess_token"):
            raise ValueError("Device is locked or session token unavailable")

        return device_info["sess_token"]

    def logout(self) -> None:
        """Logout from router."""
        try:
            # Check if we are logged in.
            if self.login_data is None or not self.session:
                return

            r = self.session.post(
                f"https://{self.host}?_type=loginData&_tag=logout_entry",
                data={"IF_LogOff": "1"},
                verify=self.verify_ssl,
                timeout=10,
            )
            self.log_request(r)
            r.raise_for_status()
            _LOGGER.debug("Logged out successfully")

        except Exception as e:
            _LOGGER.error("Failed to logout: %s", e)
        finally:
            if self.session:
                self.session.close()
                self.session = None
            self.login_data = None

    def get_devices_response(self) -> list[dict[str, Any]] | None:
        """Get the list of devices with connection reuse optimization."""
        try:
            # Combine LAN and WiFi requests for efficiency
            lan_devices = self.get_lan_devices()
            wifi_devices = self.get_wifi_devices()

            if lan_devices is None and wifi_devices is None:
                return None

            # Combine results, handling None cases
            devices = []
            if lan_devices:
                devices.extend(lan_devices)
            if wifi_devices:
                devices.extend(wifi_devices)

            return devices

        except Exception as e:
            _LOGGER.error("Error getting device response: %s", e)
            return None

    def get_lan_devices(self) -> list[dict[str, Any]] | None:
        """Get the list of devices connected to the LAN ports."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            # First request to set up context
            r = self.session.get(
                f"https://{self.host}/?_type={self.paths['type_first_request']}&_tag=localNetStatus&_={self.get_guid()}",
                verify=self.verify_ssl,
                timeout=10,
            )
            self.log_request(r)
            r.raise_for_status()

            # Main request for LAN devices
            lan_request = f"https://{self.host}/?_type={self.paths['type_main_request']}&_tag={self.paths['lan_script']}&_={self.get_guid()}"
            r = self.session.get(lan_request, verify=self.verify_ssl, timeout=10)
            self.log_request(r)
            r.raise_for_status()

            devices = self.parse_devices(r.text, self.paths["lan_id_element"], "LAN")
            self.statusmsg = "OK"
            return devices

        except Exception as e:
            self.statusmsg = f"Failed to get LAN devices: {e}"
            _LOGGER.error(self.statusmsg)
            return None

    def get_wifi_devices(self) -> list[dict[str, Any]] | None:
        """Get the list of devices connected to the wifi."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            # Since we might have already called the menu view for LAN,
            # we can try to skip it for efficiency, but keep it for safety
            try:
                # Try direct request first
                wlan_request = f"https://{self.host}/?_type={self.paths['type_main_request']}&_tag={self.paths['wlan_script']}&_={self.get_guid()}"
                r = self.session.get(wlan_request, verify=self.verify_ssl, timeout=10)
                r.raise_for_status()
            except Exception:
                # Fallback to full setup if direct request fails
                r = self.session.get(
                    f"https://{self.host}/?_type={self.paths['type_first_request']}&_tag=localNetStatus&_={self.get_guid()}",
                    verify=self.verify_ssl,
                    timeout=10,
                )
                r.raise_for_status()

                wlan_request = f"https://{self.host}/?_type={self.paths['type_main_request']}&_tag={self.paths['wlan_script']}&_={self.get_guid()}"
                r = self.session.get(wlan_request, verify=self.verify_ssl, timeout=10)
                r.raise_for_status()

            self.log_request(r)
            devices = self.parse_devices(r.text, self.paths["wlan_id_element"], "WLAN")
            self.statusmsg = "OK"
            return devices

        except Exception as e:
            self.statusmsg = f"Failed to get WiFi devices: {e}"
            _LOGGER.error(self.statusmsg)
            return None

    def get_router_details(self) -> dict[str, Any] | None:
        """Get router details."""
        try:
            if not self.session:
                raise RuntimeError("Session not initialized")

            # call first: https://10.0.0.1/?_type=menuView&_tag=statusMgr&Menu3Location=0&_=1756620757061
            url = f"https://{self.host}/?_type=menuView&_tag=statusMgr&Menu3Location=0&_={self.get_guid()}"
            r = self.session.get(url, verify=self.verify_ssl, timeout=10)
            r.raise_for_status()
            self.log_request(r)

            url = f"https://{self.host}/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_={self.get_guid()}"
            r = self.session.get(url, verify=self.verify_ssl, timeout=10)
            r.raise_for_status()
            self.log_request(r)
            # Router details.
            router_details = {}

            # Parse XML response (see routers/RouterDetail.md)
            xml = ET.fromstring(r.text)

            # node OBJ_CPUMEMUSAGE_ID has CpuUsage1 to CpuUsage4, MemUsage.
            cpu_node = xml.find("OBJ_CPUMEMUSAGE_ID/Instance")
            if cpu_node:
                # ElementTree elements do not provide getnext(), so iterate children in pairs:
                children = list(cpu_node)
                for i in range(0, len(children), 2):
                    name_elem = children[i]
                    value_elem = children[i + 1] if i + 1 < len(children) else None
                    pname = name_elem.text if name_elem is not None else None
                    pvalue = value_elem.text if value_elem is not None else None
                    if pname and pvalue and pname != "_InstID":
                        router_details[pname] = int(pvalue) if pvalue is not None and pvalue.isdigit() else pvalue
            # node OBJ_POWERONTIME_ID has PowerOnTime.
            power_node = xml.find("OBJ_POWERONTIME_ID/Instance")
            if power_node:
                # ElementTree elements do not provide getnext(), so iterate children in pairs:
                children = list(power_node)
                for i in range(0, len(children), 2):
                    name_elem = children[i]
                    value_elem = children[i + 1] if i + 1 < len(children) else None
                    pname = name_elem.text if name_elem is not None else None
                    pvalue = value_elem.text if value_elem is not None else None
                    if pname and pvalue and pname != "_InstID":
                        if pname == "PowerOnTime":
                            router_details[pname] = int(pvalue) if pvalue is not None and pvalue.isdigit() else pvalue
                        else:
                            router_details[pname] = pvalue
            return router_details

        except Exception as e:
            _LOGGER.error("Error fetching router details: %s", e)
            return None

    def get_wan_status(self) -> dict[str, Any]:
        """Fetch WAN status and return relevant attributes."""
        wan_attrs = {}
        try:
            # # Fetch MenuView first.
            url = f"https://{self.host}/?_type={self.paths['type_first_request']}&_tag={self.paths['tag_wan_status_view']}&_={self.get_guid()}"
            r = self.session.get(url, verify=self.verify_ssl, timeout=10)
            r.raise_for_status()
            # Fetch MenuData.
            url = f"https://{self.host}/?_type={self.paths['type_main_request']}&_tag={self.paths['tag_wan_status_data']}&_={self.get_guid()}"
            r = self.session.get(url, verify=self.verify_ssl, timeout=10)
            r.raise_for_status()
            self.log_request(r)
            xml = ET.fromstring(r.text)
            instances = xml.findall("ID_WAN_COMFIG/Instance")
            # Check error in response.
            error_str = xml.findtext("IF_ERRORSTR")
            if error_str and error_str not in ("SUCC", "SUCCESS", "OK"):
                _LOGGER.error("Router error: %s", error_str)
                raise Exception(f"Router error: {error_str}")

            wan_node = None
            for inst in instances:
                for i in range(0, len(inst) // 2):
                    pname = inst[i * 2].text
                    pvalue = inst[i * 2 + 1].text
                    if pname == "WANCName" and pvalue == "WAN_internet":
                        wan_node = inst
                        break
                if wan_node:
                    break
            if wan_node is None and instances:
                wan_node = instances[0]
            if wan_node:
                for i in range(0, len(wan_node) // 2):
                    pname = wan_node[i * 2].text
                    pvalue = wan_node[i * 2 + 1].text
                    if pname == "UpTime":
                        wan_attrs["WAN_uptime"] = int(pvalue)
                    elif pname == "ConnError":
                        wan_attrs["WAN_error_message"] = pvalue
                    elif pname == "RemainLeaseTime":
                        wan_attrs["WAN_remain_leasetime"] = int(pvalue)
                    elif pname == "ConnStatus":
                        wan_attrs["WAN_connected"] = pvalue == "Connected"
        except Exception as ex:
            _LOGGER.warning(f"Failed to fetch WAN status: {ex}")
        return wan_attrs

    def log_request(self, r):
        # Get cookie value for debugging.
        if not r or not r.request:
            return
        #sid = self.session.cookies.get('SID_HTTPS_')

        _LOGGER.debug(
            "Request %d URL: %s Headers: %s",
            r.status_code,
            r.request.url,
            dict(r.request.headers),
        )
        # Don't log response content in debug to avoid potential security issues
        # _LOGGER.debug("Response status: %d", r.status_code)

    def parse_devices(
        self,
        xml_response: str,
        node_name: str = "OBJ_WLAN_AD_ID",
        network_type: str = "WLAN",
    ) -> list[dict[str, Any]]:
        """Parse the xml response and return a list of devices."""
        devices = []

        try:
            if not xml_response.strip():
                _LOGGER.warning("Empty XML response received")
                return devices

            xml = ET.fromstring(xml_response)
            if xml.tag != "ajax_response_xml_root":
                _LOGGER.warning("Unexpected XML root tag: %s", xml.tag)
                raise Exception("Invalid XML format")
            # If contains IF_ERRORSTR then response is in error.
            error_str = xml.findtext("IF_ERRORSTR")
            if error_str and error_str not in ("SUCC", "SUCCESS", "OK"):
                _LOGGER.error("Router error: %s", error_str)
                raise Exception(f"Router error: {error_str}")

            # Parse WLAN AP info for ESSID mapping
            wlanap_map = {}
            for ap_instance in xml.findall("OBJ_WLANAP_ID/Instance"):
                ap_id = None
                essid = None
                for i in range(0, len(ap_instance) // 2):
                    pname = ap_instance[i * 2].text
                    pvalue = ap_instance[i * 2 + 1].text
                    if pname == "_InstID":
                        ap_id = pvalue
                    elif pname == "ESSID":
                        essid = pvalue
                if ap_id and essid:
                    wlanap_map[ap_id] = essid

            instances = xml.findall(f"{node_name}/Instance")
            _LOGGER.debug("Found %d device instances in XML", len(instances))

            for device in instances:
                device_info = {
                    "Active": True,
                    "IconType": None,
                    "NetworkType": network_type,
                    "MACAddress": "",
                    "IPAddress": "",
                    "HostName": "",
                    "Port": "",  # LAN port or WLAN ESSID
                    "LinkTime": "",
                    "ConnectTime": "",
                }

                # Parse device parameters
                child_count = len(device)
                if child_count % 2 != 0:
                    _LOGGER.warning(
                        "Unexpected device XML structure, child count: %d", child_count
                    )
                    continue

                for i in range(0, child_count // 2):
                    try:
                        param_name = device[i * 2].text
                        param_value = device[i * 2 + 1].text

                        if param_name and param_value:
                            pname = param_name.strip()
                            pvalue = param_value.strip()
                            if pname == "MACAddress":
                                device_info["MACAddress"] = pvalue.upper()
                            elif pname == "IPAddress":
                                device_info["IPAddress"] = pvalue
                            elif pname == "HostName":
                                device_info["HostName"] = pvalue
                            elif pname == "IconType":
                                device_info["IconType"] = pvalue
                            elif pname == "Active":
                                device_info["Active"] = pvalue.lower() in (
                                    "1",
                                    "true",
                                    "yes",
                                )
                            elif pname == "LinkTime":
                                device_info["LinkTime"] = pvalue
                            elif pname == "ConnectTime":
                                # Parse pvalue 2025/11/17 Mon 14:23:45 into HA datetime ISO Format.
                                try:
                                    dt = datetime.datetime.strptime(pvalue, "%Y/%m/%d %a %H:%M:%S")
                                    device_info["ConnectTime"] = dt.isoformat()
                                except ValueError:
                                    device_info["ConnectTime"] = pvalue
                            elif pname == "AliasName":  # Contains the LAN port.
                                device_info["Port"] = pvalue

                    except (IndexError, AttributeError) as e:
                        _LOGGER.warning("Error parsing device parameter %d: %s", i, e)
                        continue

                # Remap Port from WLAN AP map
                if device_info["Port"] and device_info["Port"] in wlanap_map:
                    device_info["Port"] = wlanap_map[device_info["Port"]]

                # Only add devices with valid MAC addresses
                if device_info["MACAddress"]:
                    devices.append(device_info)
                else:
                    _LOGGER.debug(
                        "Skipping device without MAC address: %s", device_info
                    )

        except ET.ParseError as e:
            _LOGGER.error("Failed to parse XML response: %s", e)
            _LOGGER.debug("XML content: %s", xml_response[:500])
            raise e

        _LOGGER.debug("Parsed %d valid devices", len(devices))
        return devices

    def reboot(self) -> bool:
        """Reboot the router using the secure endpoint."""
        try:
            if not self.login():
                _LOGGER.error("Login failed: %s", self.statusmsg)
                return False

            # First load menuView url https://10.0.0.1/?_type=menuView&_tag=rebootAndReset&Menu3Location=0&_=1756621946066
            menu_view_url = f"https://{self.host}/?_type=menuView&_tag=rebootAndReset&Menu3Location=0&_={self.get_guid()}"
            r = self.session.get(menu_view_url, verify=self.verify_ssl, timeout=30)
            self.log_request(r)
            r.raise_for_status()

            # Now prepare the reboot request.
            session_token = self.get_session_token()
            if not session_token:
                self.statusmsg = "Session token missing after login"
                _LOGGER.error(self.statusmsg)
                return False

            post_data = f"IF_ACTION=Restart&Btn_restart=&_sessionTOKEN={session_token}"
            digest_str = hashlib.sha256(post_data.encode("utf-8")).hexdigest()
            # F6600P uses a 4096-bit RSA key, other models use 2048-bit
            if self.model == "F6600P":
                pub_key_pem = (
                    "-----BEGIN PUBLIC KEY-----\n"
                    "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwlo/vZBnSJ2MyJ0dbNcw\n"
                    "DvzPqBN+O/BPvLX93GIJVSZmquJHD9X6Xn6VYeM9mRKzjEbXPlv73Dj/gjjtNj9j\n"
                    "Tq2QVyW2Sd4ZkY9e3h1ALCCCfkbjnmSqedyrcvXriTeW+J65jhBje6lTJbafmC5q\n"
                    "bGiItjt0OeOkT+Vb4S7hYPSWIjeYYBh+7Y/fg25Rt2a+RgC8dahvJ3ttB1LHXADr\n"
                    "oCm6q7G+lpbRAlpC8jjc0rZdS0c6HcBoYgzW8vxjj2fTuFy3CZZTrpPyTv/C8K6B\n"
                    "hjTnjRe6ocgFVyQ0RIYfx2hxSJcuauR57OzfMzlgFQv3RAXguDZtuVUFLO2sAiwL\n"
                    "ELph3Acfy9Eh58SHcswZvsOSXY0JNb0XeRM9gxpntLRfM6TB7f9hYtYTDw5oKdyN\n"
                    "BY+nnEa/IpBUjndGDrSs3Z4BxRbYcJEwkKQZkvw/5TpQYbkD6sTRVSlZPaXSjeCl\n"
                    "0hsLCttqwJqRZcjbWXrINBYFw8PYE14Xr9BCyPgqocdQh7FgvasVgG6u5mLR1PBZ\n"
                    "o4EFF/LdY0yvMG5rl9egBk1XD/UMayhRtmSQEUzYt3eEWLBbqJB6MbVJ2ygcv5EL\n"
                    "ReDY0SWXw1PIEbHeP51A/MyB6kwSgZwdoQW3JiaPnGHMaE0NqfAYPNiGJLMsmvT/\n"
                    "rNUI/8iSCW+WvSzx9tByUxsCAwEAAQ==\n"
                    "-----END PUBLIC KEY-----"
                )
            else:
                pub_key_pem = (
                    "-----BEGIN PUBLIC KEY-----\n"
                    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAodPTerkUVCYmv28SOfRV\n"
                    "7UKHVujx/HjCUTAWy9l0L5H0JV0LfDudTdMNPEKloZsNam3YrtEnq6jqMLJV4ASb\n"
                    "1d6axmIgJ636wyTUS99gj4BKs6bQSTUSE8h/QkUYv4gEIt3saMS0pZpd90y6+B/9\n"
                    "hZxZE/RKU8e+zgRqp1/762TB7vcjtjOwXRDEL0w71Jk9i8VUQ59MR1Uj5E8X3WIc\n"
                    "fYSK5RWBkMhfaTRM6ozS9Bqhi40xlSOb3GBxCmliCifOJNLoO9kFoWgAIw5hkSIb\n"
                    "GH+4Csop9Uy8VvmmB+B3ubFLN35qIa5OG5+SDXn4L7FeAA5lRiGxRi8tsWrtew8w\n"
                    "nwIDAQAB\n"
                    "-----END PUBLIC KEY-----"
                )

            public_key = serialization.load_pem_public_key(pub_key_pem.encode("utf-8"))
            encrypted_digest = public_key.encrypt(
                digest_str.encode("utf-8"), padding.PKCS1v15()
            )
            check_header = base64.b64encode(encrypted_digest).decode("utf-8")

            headers = {
                "Check": check_header,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            url = f"https://{self.host}/?_type=menuData&_tag=devmgr_restartmgr_lua.lua&_={self.get_guid()}"
            r = self.session.post(
                url, data=post_data, headers=headers, verify=self.verify_ssl, timeout=30
            )
            self.log_request(r)
            r.raise_for_status()
            # Check error in response.
            xml = ET.fromstring(r.content)
            error_str = xml.findtext("IF_ERRORSTR")
            if error_str and error_str not in ("SUCC", "SUCCESS", "OK"):
                _LOGGER.error("Router error: %s", error_str)
                _LOGGER.debug("Reboot response XML: %s", r.text)
                raise Exception(f"Router error: {error_str}")

            self.statusmsg = "Reboot command sent successfully."
            return True
        except Exception as e:
            self.statusmsg = f"Failed to reboot: {e}"
            _LOGGER.error(self.statusmsg)
            return False
        finally:
            self.logout()
