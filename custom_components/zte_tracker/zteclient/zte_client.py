"""ZTE router client with improved security and error handling."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import requests
import xml.etree.ElementTree as ET
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "DNT": "1",
        })
        
        self.session.cookies.set("_TESTCOOKIESUPPORT", "1")

    def reboot(self) -> bool:
        """Reboot the router."""
        if not self.login():
            return False
        
        _LOGGER.info("Requesting router reboot")
        try:
            # Note: Reboot functionality needs to be implemented based on router model
            raise NotImplementedError("Reboot functionality not yet implemented")
        except Exception as e:
            _LOGGER.error("Failed to reboot: %s", e)
            return False
        finally:
            self.logout()

    def login(self) -> bool:
        """Login procedure using ZTE challenge."""
        try:
            self._setup_session()

            # Step1: Get session token
            session_token = self.get_session_token()

            # Step2: Query for login token
            r = self.session.get(
                f"http://{self.host}/?_type=loginData&_tag=login_token&_={self.get_guid()}",
                verify=self.verify_ssl,
                timeout=10,
            )
            self.log_request(r)
            r.raise_for_status()
            
            # Parse XML response
            xml_response = ET.fromstring(r.content)
            if xml_response.tag != "ajax_response_xml_root":
                raise ValueError(f"Unexpected response format: {xml_response.tag}")
            
            login_token = xml_response.text
            if not login_token:
                raise ValueError("Empty login_token")

            # Step3: Login entry
            pass_hash = self.password + login_token
            password_param = hashlib.sha256(pass_hash.encode()).hexdigest()

            r = self.session.post(
                f"http://{self.host}/?_type=loginData&_tag=login_entry",
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
            
            # Handle refresh requirement
            if self.login_data.get("login_need_refresh") == 1:
                _LOGGER.debug("Login refresh required")
            
            self.statusmsg = None
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
            f"http://{self.host}/?_type=loginData&_tag=login_entry",
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
                f"http://{self.host}?_type=loginData&_tag=logout_entry",
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

    def get_devices_response(self):
        """
        Get the list of devices
        """
        lan_devices = self.get_lan_devices()
        wifi_devices = self.get_wifi_devices()
        devices = wifi_devices + lan_devices
        return devices

    def get_lan_devices(self):
        """
        Get the list of devices connected to the LAN ports
        :return: list of devices
        """
        # GET DEVICES RESPONSE from http://10.0.0.1/?_type=menuData&_tag=accessdev_homepage_lua.lua&InstNum=5&_=1663922344910
        try:
            r = self.session.get(
                "http://{0}/?_type=menuView&_tag=localNetStatus&_={1}".format(
                    self.host, self.get_guid()
                ),
                verify=True,  # Enable SSL verification
                timeout=10,   # Add timeout
            )
            lan_request = "http://{0}/?_type=menuData&_tag={1}&_{2}".format(
                self.host, self.paths["lan_script"], self.get_guid()
            )
            r = self.session.get(lan_request, verify=True, timeout=10)
            self.log_request(r)
            devices = self.parse_devices(r.text, self.paths["lan_id_element"], "LAN")
            self.statusmsg = "OK"
            return devices
        except Exception as e:
            self.statusmsg = "Failed to get LAN devices: {0}".format(e)
            _LOGGER.error(self.statusmsg)
            return []

    def get_wifi_devices(self):
        """
        Get the list of devices connected to the wifi
        :return: list of devices
        """
        # GET DEVICES RESPONSE
        try:
            r = self.session.get(
                "http://{0}/?_type=menuView&_tag=localNetStatus&_={1}".format(
                    self.host, self.get_guid()
                ),
                verify=True,  # Enable SSL verification
                timeout=10,   # Add timeout
            )
            wlan_request = "http://{0}/?_type=menuData&_tag={1}&_={2}".format(
                self.host, self.paths["wlan_script"], self.get_guid()
            )
            r = self.session.get(wlan_request, verify=True, timeout=10)
            self.log_request(r)
            devices = self.parse_devices(r.text, self.paths["wlan_id_element"], "WLAN")

            self.statusmsg = "OK"
        except Exception as e:
            self.statusmsg = "Failed to get Devices: {0}  rdev {2}".format(e, r.content)
            _LOGGER.error(self.statusmsg)
            return []

        return devices

    def log_request(self, r):
        _LOGGER.debug("Request URL: %s", r.request.url)
        _LOGGER.debug("Request headers: %s", dict(r.request.headers))
        # Don't log response content in debug to avoid potential security issues
        _LOGGER.debug("Response status: %d", r.status_code)

    # Parse xml response to get devices
    def parse_devices(
        self, xml_response, node_name="OBJ_WLAN_AD_ID", network_type="WLAN"
    ):
        """Parse the xml response and return a list of devices."""
        devices = []
        xml = ET.fromstring(xml_response)
        assert xml.tag == "ajax_response_xml_root", (
            "Unexpected response " + xml_response
        )

        for device in xml.findall(f"{node_name}/Instance"):
            device_info = {
                "Active": True,
                "IconType": None,
                "NetworkType": network_type,
            }
            for i in range(0, int(len(device) / 2)):
                paramname = device[i * 2].text
                paramvalue = device[i * 2 + 1].text
                if paramname == "MACAddress":
                    device_info["MACAddress"] = paramvalue
                elif paramname == "IPAddress":
                    device_info["IPAddress"] = paramvalue
                elif paramname == "HostName":
                    device_info["HostName"] = paramvalue
            devices.append(device_info)
        return devices
