from array import array
import logging
import re
import json
import hashlib
import time
from requests import Session
import xml.etree.ElementTree as ET


_LOGGER = logging.getLogger(__name__)


class zteClient:
    def __init__(self, host, username, password):
        """Initialize the client."""
        self.statusmsg = None
        self.host = host
        self.username = username
        self.password = password
        self.session = None
        self.login_data = None
        self.status = 'off'
        self.device_info = None
        self.guid = int(time.time()*1000)

    # REBOOT THE ROUTER
    def reboot(self) -> bool:
        if not self.login:
            return False
        # REBOOT REQUEST
        _LOGGER.info("Requesting reboot")
        try:
            data = {
                'csrf': {'csrf_param': self.login_data['csrf_param'], 'csrf_token': self.login_data['csrf_token']}}
            r = self.session.post('https://{0}/api/service/reboot.cgi'.format(self.host),
                                  data=json.dumps(data, separators=(',', ':')))
            data = json.loads(re.search('({.*?})', r.text).group(1))
            assert data['errcode'] == 0, data
            _LOGGER.info("Rebooting HG659")
            return True
        except Exception as e:
            _LOGGER.error('Failed to reboot: {0} with data {1}'.format(e, data))
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
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'})
            self.session.headers.update({'DNT': '1'})
            self.session.cookies.set('_TESTCOOKIESUPPORT', '1')

            # Step1: Get session token.
            session_token = self.get_session_token()
           
            # Step2: query for login token.
            r = self.session.get('http://{0}/?_type=loginData&_tag=login_token&_={1}'.format(self.host, self.get_guid() ), verify=False)
            self.log_request(r)
            # parse XML response.
            xml_response = ET.fromstring(r.content)
            assert xml_response.tag == 'ajax_response_xml_root', 'Unexpected response ' + xml_response.text
            login_token = xml_response.text
            assert login_token, 'Empty login_token'
     
            # Step3: Login entry
            pass_hash = self.password + login_token
            password_param = hashlib.sha256(pass_hash.encode()).hexdigest()

            r = self.session.post("http://{0}/?_type=loginData&_tag=login_entry".format(self.host),verify=False,
                data= { "action": "login", "Password": password_param, "Username": self.username, "_sessionTOKEN": session_token })
            self.log_request(r)
            self.login_data = r.json()
            # if login need refresh make a new request.
            if self.login_data['login_need_refresh'] == 1:
                print("REFRESH")
                # r = self.session.get('http://{0}/'.format(self.host), verify=False)
                # self.log_request(r)
            self.statusmsg = None
          
            return True
        except Exception as e:
            _LOGGER.error('Failed to login: {0}'.format(e))
            self.statusmsg = 'Failed login: {0}'.format(e)
            self.login_data = None
            self.session.close()
            return False

    def get_guid(self):
        guid = self.guid
        self.guid +=1
        return guid

    def get_session_token(self):
        r = self.session.get('http://{0}/?_type=loginData&_tag=login_entry'.format(self.host),verify=False)
        self.log_request(r)
        self.status = 'on'
        device_info = r.json()
        assert device_info['lockingTime'] == 0 and device_info['sess_token'], 'Empty sess_token. Device locked?'
        session_token = device_info['sess_token']
        return session_token

    ## LOGOUT ##
    def logout(self):
        try:
            if self.login_data is None:
                return False
    
            r = self.session.post('http://{0}?_type=loginData&_tag=logout_entry'.format(self.host),
                     data={'IF_LogOff':'1'}, verify=False)
            self.log_request(r)
            
            assert r.ok, r
            _LOGGER.debug("Logged out")
        except Exception as e:
            _LOGGER.error('Failed to logout: {0}'.format(e))
        finally:
            self.session.close()
            self.login_data = None

    def get_devices_response(self):
        """Get the raw string with the devices from the router."""
        # GET DEVICES RESPONSE
        try:
            # r= self.session.get('http://10.0.0.1/?_type=menuData&_tag=wlan_homepage_lua.lua&InstNum=5&_={0}'.format(self.get_guid()), verify=False)
            # self.log_request(r)
            r= self.session.get('http://{0}/?_type=menuView&_tag=localNetStatus&_={1}'.format(self.host, self.get_guid()),verify=False)
            self.log_request(r)
            # r= self.session.get('http://10.0.0.1/?_type=menuData&_tag=status_lan_info_lua.lua&_={0}'.format(self.get_guid()),verify=False)
            # self.log_request(r)
            # r= self.session.get('http://10.0.0.1/?_type=hiddenData&_tag=sntp_data&_={0}'.format(self.get_guid()),verify=False)
            # self.log_request(r)
            r= self.session.get('http://{0}/?_type=menuData&_tag=wlan_client_stat_lua.lua&_={1}'.format(self.host, self.get_guid()),verify=False)
            self.log_request(r)
            devices = self.parse_devices(r.text)
            
            self.statusmsg = 'OK'
        except Exception as e:
            _LOGGER.error('Failed to get Devices: {0}  rdev {2}'.format(e,  r.content))
            self.statusmsg = "Failed to get Devices"
            return False
        return devices

    def log_request(self, r):
        _LOGGER.debug(r.request.url)
        _LOGGER.debug(r.request.headers)
        _LOGGER.debug(r.text[0:200])
    
    # Parse xml response to get devices
    def parse_devices(self, xml_response):
        """Parse the xml response and return a list of devices."""
        devices = []
        xml = ET.fromstring(xml_response)
        assert xml.tag == 'ajax_response_xml_root', 'Unexpected response ' + xml_response
        
        for device in xml.findall('OBJ_WLAN_AD_ID/Instance'):
            device_info = {'Active': True, "IconType": None }
            for i in range(0, int(len(device)/2)):
                paramname = device[i*2].text
                paramvalue = device[i*2+1].text
                if paramname == 'MACAddress':
                    device_info['MACAddress'] = paramvalue
                elif paramname == 'IPAddress':
                    device_info['IPAddress'] = paramvalue
                elif paramname == 'HostName':
                    device_info['HostName'] = paramvalue
            devices.append(device_info)
        return devices

