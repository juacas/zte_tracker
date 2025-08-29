from array import array
import logging
import re
import json
import hashlib
import time
from requests import Session
import xml.etree.ElementTree as ET

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
# Synonym H169A is like H288A
_MODELS["H169A"] = _MODELS["H288A"]
# Synonym H388X is like  H288A
_MODELS["H388X"] = _MODELS["H288A"]
# Synonym H2640 is like H388X
_MODELS["H2640"] = _MODELS["H288A"]
# Synonym F6645P is like F6640
_MODELS["F6645P"] = _MODELS["F6640"]
# Synonym H3600P is like H288A
_MODELS["H3600P"] = _MODELS["H288A"]
# Synonym H6645P is like H288A
_MODELS["H6645P"] = _MODELS["H288A"]
# Synonym H3640 is like H288A
_MODELS["H3640"] = _MODELS["H288A"]
class zteClient:
    def __init__(self, host, username, password, model):
        """Initialize the client."""
        self.statusmsg = None
        self.host = host
        self.username = username
        self.password = password
        self.session = None
        self.login_data = None
        self.status = "on"
        self.device_info = None
        self.guid = int(time.time() * 1000)
        self.model = model
        self.paths = _MODELS[model]

    # Retuns the list of supported model keys.
    def get_models(self) -> list:
        return list(_MODELS.keys())

    # REBOOT THE ROUTER
    def reboot(self) -> bool:
        if not self.login:
            return False
        # REBOOT REQUEST
        _LOGGER.info("Requesting reboot")
        try:
            raise Exception("Not implemented")
        except Exception as e:
            _LOGGER.error("Failed to reboot: {0}".format(e))
            return False
        finally:
            self.logout()

    # LOGIN PROCEDURE
    def login(self) -> bool:
        """
        Login procedure using ZTE challenge
        :return: true if the login has succeeded
        """
        try:
            self.session = Session()
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
                }
            )
            self.session.headers.update({"DNT": "1"})
            self.session.cookies.set("_TESTCOOKIESUPPORT", "1")

            # Step1: Get session token.
            session_token = self.get_session_token()

            # Step2: query for login token.
            r = self.session.get(
                "http://{0}/?_type=loginData&_tag=login_token&_={1}".format(
                    self.host, self.get_guid()
                ),
                verify=False,
            )
            self.log_request(r)
            # parse XML response.
            xml_response = ET.fromstring(r.content)
            assert xml_response.tag == "ajax_response_xml_root", (
                "Unexpected response " + xml_response.text
            )
            login_token = xml_response.text
            assert login_token, "Empty login_token"

            # Step3: Login entry
            pass_hash = self.password + login_token
            password_param = hashlib.sha256(pass_hash.encode()).hexdigest()

            r = self.session.post(
                "http://{0}/?_type=loginData&_tag=login_entry".format(self.host),
                verify=False,
                data={
                    "action": "login",
                    "Password": password_param,
                    "Username": self.username,
                    "_sessionTOKEN": session_token,
                },
            )
            self.log_request(r)
            self.login_data = r.json()
            # if login need refresh make a new request.
            if self.login_data["login_need_refresh"] == 1:
                _LOGGER.debug("REFRESH")
                # r = self.session.get('http://{0}/'.format(self.host), verify=False)
                # self.log_request(r)
            self.statusmsg = None

            return True
        except Exception as e:
            self.statusmsg = "Failed login: {0}".format(e)
            _LOGGER.error(self.statusmsg)
            self.login_data = None
            self.session.close()
            return False

    def get_guid(self):
        guid = self.guid
        self.guid += 1
        return guid

    def get_session_token(self):
        r = self.session.get(
            "http://{0}/?_type=loginData&_tag=login_entry".format(self.host),
            verify=False,
            timeout=1, # timeout 1 second
        )
        self.log_request(r)
        self.status = "on"
        device_info = r.json()
        assert (
            device_info["lockingTime"] == 0 and device_info["sess_token"]
        ), "Empty sess_token. Device locked?"
        session_token = device_info["sess_token"]
        return session_token

    ## LOGOUT ##
    def logout(self):
        try:
            if self.login_data is None:
                return False

            r = self.session.post(
                "http://{0}?_type=loginData&_tag=logout_entry".format(self.host),
                data={"IF_LogOff": "1"},
                verify=False,
            )
            self.log_request(r)

            assert r.ok, r
            _LOGGER.debug("Logged out")
        except Exception as e:
            _LOGGER.error("Failed to logout: {0}".format(e))
        finally:
            self.session.close()
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
                verify=False,
            )
            lan_request = "http://{0}/?_type=menuData&_tag={1}&_{2}".format(
                self.host, self.paths["lan_script"], self.get_guid()
            )
            r = self.session.get(lan_request, verify=False)
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
                verify=False,
            )
            wlan_request = "http://{0}/?_type=menuData&_tag={1}&_={2}".format(
                self.host, self.paths["wlan_script"], self.get_guid()
            )
            r = self.session.get(wlan_request, verify=False)
            self.log_request(r)
            devices = self.parse_devices(r.text, self.paths["wlan_id_element"], "WLAN")

            self.statusmsg = "OK"
        except Exception as e:
            self.statusmsg = "Failed to get Devices: {0}  rdev {2}".format(e, r.content)
            _LOGGER.error(self.statusmsg)
            return []

        return devices

    def log_request(self, r):
        _LOGGER.debug(r.request.url)
        _LOGGER.debug(r.request.headers)
        _LOGGER.debug(r.text[0:200])

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