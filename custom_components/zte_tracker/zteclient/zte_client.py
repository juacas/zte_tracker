from __future__ import annotations

"""ZTE router client with improved security and error handling."""

import hashlib
import logging
import time
from typing import Any
import warnings
import xml.etree.ElementTree as ET

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
    },
    "H288A": {
        "wlan_script": "accessdev_ssiddev_lua.lua",
        "wlan_id_element": "OBJ_ACCESSDEV_ID",
        "lan_script": "accessdev_landevs_lua.lua",
        "lan_id_element": "OBJ_ACCESSDEV_ID",
    },
}

# Add synonyms
_MODELS["H169A"] = _MODELS["H288A"]
_MODELS["H388X"] = _MODELS["H288A"]
_MODELS["H2640"] = _MODELS["H288A"]
_MODELS["F6645P"] = _MODELS["F6640"]
_MODELS["H3600P"] = _MODELS["H288A"]
_MODELS["H6645P"] = _MODELS["H288A"]
_MODELS["H3640"] = _MODELS["H288A"]
_MODELS["BE5100"] = _MODELS["F6640"]  # Chinese model, use root username


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

        self.session.cookies.set("_TESTCOOKIESUPPORT", "1")

    def reboot(self) -> bool:
        """Reboot the router."""
        try:
            # Note: Reboot functionality needs to be implemented based on router model
            raise NotImplementedError("Reboot functionality not yet implemented")
            if not self.login():
                return False

            _LOGGER.info("Requesting router reboot")
        except Exception as e:
            _LOGGER.error("Failed to reboot: %s", e)
            return False
        finally:
            self.logout()

    def login(self) -> bool:
        """Login procedure using ZTE challenge. Returns True if successful, False otherwise. Sets statusmsg for error reporting."""
        try:
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
                f"https://{self.host}/?_type=menuView&_tag=localNetStatus&_={self.get_guid()}",
                verify=self.verify_ssl,
                timeout=10,
            )
            self.log_request(r)
            r.raise_for_status()

            # Main request for LAN devices
            lan_request = f"https://{self.host}/?_type=menuData&_tag={self.paths['lan_script']}&_{self.get_guid()}"
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
                wlan_request = f"https://{self.host}/?_type=menuData&_tag={self.paths['wlan_script']}&_={self.get_guid()}"
                r = self.session.get(wlan_request, verify=self.verify_ssl, timeout=10)
                r.raise_for_status()
            except Exception:
                # Fallback to full setup if direct request fails
                r = self.session.get(
                    f"https://{self.host}/?_type=menuView&_tag=localNetStatus&_={self.get_guid()}",
                    verify=self.verify_ssl,
                    timeout=10,
                )
                r.raise_for_status()

                wlan_request = f"https://{self.host}/?_type=menuData&_tag={self.paths['wlan_script']}&_={self.get_guid()}"
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

    def log_request(self, r):
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
