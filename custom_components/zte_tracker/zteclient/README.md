## Login Steps
Personal Notes for reverse-engineering.

### Step 1
Ct--> date.now() --> _=1663400461404

http://10.0.0.1/?_type=loginData&_tag=login_token&_=1663400461404

var loadAllowAddr = "/?_type=loginData&_tag=login_token";
$(this).dataTransfer(loadAllowAddr, "GET", g_loginToken, undefined, false);

Resp:_ <ajax_response_xml_root>68877896</ajax_response_xml_root>

### Step 2

fetch("http://10.0.0.1/?_type=loginData&_tag=login_entry", {
  "headers": {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "x-requested-with": "XMLHttpRequest"
  },
  "referrer": "http://10.0.0.1/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": null,
  "method": "GET",
  "mode": "cors",
  "credentials": "include"
});

Response:
{"lockingTime":0,"loginErrMsg":"","promptMsg":"","sess_token":"oCh5FugQaTDj5rSvKUHHKZ15"}


### Step 3
http://10.0.0.1/?_type=loginData&_tag=login_entry

function g_loginToken(xml)
{
var xmlObj = $(xml).text();
var Password =$("#Frm_Password").val();
var SHA256Password =sha256(Password+xmlObj);
var postData = {};
postData["action"] = "login";
postData["Password"] = SHA256Password;
postData["Username"] = $("#Frm_Username").val();
postData["_sessionTOKEN"] = $("#_sessionTOKEN").val();
Password = undefined;
SHA256Password = undefined;
$.post( "/?_type=loginData&_tag=login_entry", postData, undefined, "json" )
.done(function( data ) {
$("#_sessionTOKEN").val(data.sess_token);
if ( data.login_need_refresh )
{
top.location.href = top.location.href;
}
else
{
DisplayLoginErrorTip(data);
}
});


    fetch("http://10.0.0.1/?_type=loginData&_tag=login_entry", {
  "headers": {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest"
  },
  "referrer": "http://10.0.0.1/",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": "action=login&Password=db9f16152d4a23b3cb5b4a81324880a7592dc95b0c438daaa4e9fbbd&Username=admin&_sessionTOKEN=oCh5FugQaTDj5rSvKUHHKZ15",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});

b'{"lockingTime":0,"loginErrMsg":"","promptMsg":"","sess_token":"wfCJHiPDWgxBQtI0FaGyiP7D"}'

## Obtener hosts
http://10.0.0.1/?_type=menuData&_tag=wlan_client_stat_lua.lua&_=1663483694859

<ajax_response_xml_root>
 <IF_ERRORPARAM>SUCC</IF_ERRORPARAM>
 <IF_ERRORTYPE>SUCC</IF_ERRORTYPE>
 <IF_ERRORSTR>SUCC</IF_ERRORSTR>
 <IF_ERRORID>0</IF_ERRORID>
 <OBJ_WLAN_AD_ID>
  <Instance>
    <ParaName>_InstID</ParaName>
    <ParaValue>DEV.WIFI.AP1.AD1</ParaValue>
    <ParaName>AliasName</ParaName>
    <ParaValue>DEV.WIFI.AP1</ParaValue>
    <ParaName>RxRate</ParaName>
    <ParaValue>216000</ParaValue>
    <ParaName>HostName</ParaName>
    <ParaValue>LAPTOP</ParaValue>
    <ParaName>RSSI</ParaName>
    <ParaValue>-57</ParaValue>
    <ParaName>LinkTime</ParaName>
    <ParaValue>69363</ParaValue>
    <ParaName>TxRate</ParaName><ParaValue>143000</ParaValue>
    <ParaName>NOISE</ParaName><ParaValue>-89</ParaValue>
    <ParaName>IPAddress</ParaName><ParaValue>10.0.0.20</ParaValue>
    <ParaName>IPV6Address</ParaName><ParaValue>fe80::fdc7:5eac:f4b7:7f0d</ParaValue>
    <ParaName>SNR</ParaName><ParaValue>32</ParaValue>
    <ParaName>MACAddress</ParaName><ParaValue>6d:a1:05:58:b2:3b</ParaValue>
    <ParaName>CurrentMode</ParaName><ParaValue>11ax</ParaValue>
    <ParaName>MCS</ParaName><ParaValue>11</ParaValue>
    <ParaName>BAND</ParaName><ParaValue>20MHz</ParaValue>
  </Instance>

  <OBJ_WLANAP_ID>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP1</ParaValue>
      <ParaName>ESSID</ParaName><ParaValue>wifi1</ParaValue></Instance>
    <Instance>
      <ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP2</ParaValue>
      <ParaName>ESSID</ParaName><ParaValue>SSID2</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP3</ParaValue><ParaName>ESSID</ParaName><ParaValue>Guest_0FAA</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP4</ParaValue><ParaName>ESSID</ParaName><ParaValue>SSID4</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP5</ParaValue><ParaName>ESSID</ParaName><ParaValue>wifi2</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP6</ParaValue><ParaName>ESSID</ParaName><ParaValue>cococasa</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP7</ParaValue><ParaName>ESSID</ParaName><ParaValue>SSID7</ParaValue></Instance><Instance><ParaName>_InstID</ParaName><ParaValue>DEV.WIFI.AP8</ParaValue><ParaName>ESSID</ParaName><ParaValue>SSID8</ParaValue></Instance></OBJ_WLANAP_ID></ajax_response_xml_root>



      LOGOUT
      POST

      http://10.0.0.1/?_type=loginData&_tag=logout_entry

      IF_LogOff=1

## Get LAN STATUS

http://10.0.0.1/?_type=menuData&_tag=wlan_wlansssidconf_lua.lua&_=1763447302776

'''xml
<ajax_response_xml_root>
	<IF_ERRORPARAM>SUCC</IF_ERRORPARAM>
	<IF_ERRORTYPE>SUCC</IF_ERRORTYPE>
	<IF_ERRORSTR>SUCC</IF_ERRORSTR>
	<IF_ERRORID>0</IF_ERRORID>
	<OBJ_WLANAP_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP1</ParaValue>
			<ParaName>Enable</ParaName>
			<ParaValue>1</ParaValue>
			<ParaName>BeaconType</ParaName>
			<ParaValue>11i</ParaValue>
			<ParaName>WEPAuthMode</ParaName>
			<ParaValue>None</ParaValue>
			<ParaName>Alias</ParaName>
			<ParaValue>SSID1</ParaValue>
			<ParaName>ESSIDHideEnable</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>ESSID</ParaName>
			<ParaValue>ssid</ParaValue>
			<ParaName>WEPKeyIndex</ParaName>
			<ParaValue>1</ParaValue>
			<ParaName>WPA3EncryptType</ParaName>
			<ParaValue>AESEncryption</ParaValue>
			<ParaName>WPA3AuthMode</ParaName>
			<ParaValue>SAEAuthentication</ParaValue>
			<ParaName>WPAAuthMode</ParaName>
			<ParaValue>PSKAuthentication</ParaValue>
			<ParaName>WLANViewName</ParaName>
			<ParaValue>DEV.WIFI.RD1</ParaValue>
			<ParaName>WPAGroupRekey</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>11iEncryptType</ParaName>
			<ParaValue>AESEncryption</ParaValue>
			<ParaName>MaxUserNum</ParaName>
			<ParaValue>32</ParaValue>
			<ParaName>VapIsolationEnable</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>WPAEncryptType</ParaName>
			<ParaValue>TKIPandAESEncryption</ParaValue>
			<ParaName>11iAuthMode</ParaName>
			<ParaValue>PSKAuthentication</ParaValue>
		</Instance>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP2</ParaValue>
			<ParaName>Enable</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>BeaconType</ParaName>
			<ParaValue>WPAand11i</ParaValue>
			<ParaName>WEPAuthMode</ParaName>
			<ParaValue>None</ParaValue>
			<ParaName>Alias</ParaName>
			<ParaValue>SSID2</ParaValue>
			<ParaName>ESSIDHideEnable</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>ESSID</ParaName>
			<ParaValue>ssid2</ParaValue>
			<ParaName>WEPKeyIndex</ParaName>
			<ParaValue>1</ParaValue>
			<ParaName>WPA3EncryptType</ParaName>
			<ParaValue>AESEncryption</ParaValue>
			<ParaName>WPA3AuthMode</ParaName>
			<ParaValue>SAEAuthentication</ParaValue>
			<ParaName>WPAAuthMode</ParaName>
			<ParaValue>PSKAuthentication</ParaValue>
			<ParaName>WLANViewName</ParaName>
			<ParaValue>DEV.WIFI.RD1</ParaValue>
			<ParaName>WPAGroupRekey</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>11iEncryptType</ParaName>
			<ParaValue>TKIPandAESEncryption</ParaValue>
			<ParaName>MaxUserNum</ParaName>
			<ParaValue>32</ParaValue>
			<ParaName>VapIsolationEnable</ParaName>
			<ParaValue>0</ParaValue>
			<ParaName>WPAEncryptType</ParaName>
			<ParaValue>TKIPandAESEncryption</ParaValue>
			<ParaName>11iAuthMode</ParaName>
			<ParaValue>PSKAuthentication</ParaValue>
		</Instance>
		...
	</OBJ_WLANAP_ID>
	<OBJ_WLANSETTING_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.RD1</ParaValue>
			<ParaName>Band</ParaName>
			<ParaValue>2.4GHz</ParaValue>
			<ParaName>RadioStatus</ParaName>
			<ParaValue>1</ParaValue>
		</Instance>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.RD2</ParaValue>
			<ParaName>Band</ParaName>
			<ParaValue>5GHz</ParaValue>
			<ParaName>RadioStatus</ParaName>
			<ParaValue>1</ParaValue>
		</Instance>
	</OBJ_WLANSETTING_ID>
	<OBJ_WLANWEPKEY_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP1.WEP1</ParaValue>
			<ParaName>WEPKey</ParaName>
			<ParaValue>key1</ParaValue>
		</Instance>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP1.WEP2</ParaValue>
			<ParaName>WEPKey</ParaName>
			<ParaValue>key2</ParaValue>
		</Instance>
		...
	</OBJ_WLANWEPKEY_ID>
	<encode>WEPKey</encode>
	<OBJ_WLANPSK_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP1.PSK1</ParaValue>
			<ParaName>KeyPassphrase</ParaName>
			<ParaValue>password</ParaValue>
		</Instance>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.WIFI.AP2.PSK1</ParaValue>
			<ParaName>KeyPassphrase</ParaName>
			<ParaValue>password</ParaValue>
		</Instance>
		...
	</OBJ_WLANPSK_ID>
	<encode>KeyPassphrase</encode>
	<OBJ_GUESTWIFI_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.GuestWifi1</ParaValue>
			<ParaName>GuestWifi</ParaName>
			<ParaValue>0</ParaValue>
		</Instance>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>DEV.GuestWifi2</ParaValue>
			<ParaName>GuestWifi</ParaName>
			<ParaValue>0</ParaValue>
		</Instance>
		...
	</OBJ_GUESTWIFI_ID>
	<OBJ_MAP_MASTER_ID>
		<Instance>
			<ParaName>_InstID</ParaName>
			<ParaValue>IGD</ParaValue>
			<ParaName>EnBandSteer</ParaName>
			<ParaValue>0</ParaValue>
		</Instance>
	</OBJ_MAP_MASTER_ID>
</ajax_response_xml_root>

# ENABLE/DISBLE SSID

http://10.0.0.1/?_type=menuData&_tag=wlan_wlansssidconf_lua.lua

POST DATA:

IF_ACTION=Apply&Enable=1&_InstID=DEV.WIFI.AP3&_WEPCONIG=N&_PSKCONIG=Y&BeaconType=11i&WEPAuthMode=None&WPAAuthMode=PSKAuthentication&11iAuthMode=PSKAuthentication&WPAEncryptType=TKIPandAESEncryption&11iEncryptType=AESEncryption&WPA3AuthMode=SAEAuthentication&WPA3EncryptType=TKIPandAESEncryption&_InstID_WEP0=DEV.WIFI.AP3.WEP1&_InstID_WEP1=DEV.WIFI.AP3.WEP2&_InstID_WEP2=DEV.WIFI.AP3.WEP3&_InstID_WEP3=DEV.WIFI.AP3.WEP4&_InstID_PSK=DEV.WIFI.AP3.PSK1&_InstID_GUEST=DEV.GuestWifi3&MasterAuthServerIp=...&ESSID=Guest_0FAA&ESSIDHideEnable=0&EncryptionType=WPA2-PSK-AES&KeyPassphrase=xxxxxx%2BzvA%3D%3D&WEPKeyIndex=1&ShowWEPKey=0&WEPKey00=xxxxxx92lPsm74JfkQ%3D%3D&WEPKey01=xxxxxJON22K0XCC%2BUVQ%3D%3D&WEPKey02=xxx%2FPt8CcJdM47NWUggMw%3D%3D&WEPKey03=xxxxxNqLZdeccofdACQ%3D%3D&GuestWifi=1&VapIsolationEnable=1&MaxUserNum=32&sub_MasterAuthServerIp0=&sub_MasterAuthServerIp1=&sub_MasterAuthServerIp2=&sub_MasterAuthServerIp3=&MasterAuthServerPort=&MasterAuthServerSecret=&Btn_cancel_WLANSSIDConf=&Btn_apply_WLANSSIDConf=&encode=dXAu%2BxxxxS%2BKv%2Fp%2FExxxxxASW5iZ%2FAXsy9sP3z1QwIOLnUU8p58aLRP059Ei5BNYGBHBP6WfIAVxxxxxxxxx....4utwMatnR%2FNIrcvHGS13FTptqHrVSGOrWeCnwK773cZaLP0VxmDNi2X0%2BuSOR9baJi4xMXWRUIPnYnn4ADICDDKmWmz9o2HspQk6CGhM74LGyetF8SA%3D%3D&_sessionTOKEN=zrFZ1ezCISH3P2YsKAzMgml8

## REBOOT
      TODO: Implement. Need to create a encrypted request.

      POST
      http://10.0.0.1/?_type=menuData&_tag=devmgr_restartmgr_lua.lua

      IF_ACTION: Restart
      Btn_restart:
      _sessionTOKEN: 793evTKMtJEPBUNUAT7QPxzy

      Header:

      postDataTmp = "IF_ACTION=Restart&Btn_restart=&_sessionTOKEN=ST0w6eOVJrjgTCK0J72DthuZ"

      var degistStr = sha256(PostDataTmp);
      selfHeader["Check"] = asyEncode(degistStr);

       function asyEncode(srcStr) {
                            var pubKey = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAodPTerkUVCYmv28SOfRV\n7UKHVujx/HjCUTAWy9l0L5H0JV0LfDudTdMNPEKloZsNam3YrtEnq6jqMLJV4ASb\n1d6axmIgJ636wyTUS99gj4BKs6bQSTUSE8h/QkUYv4gEIt3saMS0pZpd90y6+B/9\nhZxZE/RKU8e+zgRqp1/762TB7vcjtjOwXRDEL0w71Jk9i8VUQ59MR1Uj5E8X3WIc\nfYSK5RWBkMhfaTRM6ozS9Bqhi40xlSOb3GBxCmliCifOJNLoO9kFoWgAIw5hkSIb\nGH+4Csop9Uy8VvmmB+B3ubFLN35qIa5OG5+SDXn4L7FeAA5lRiGxRi8tsWrtew8w\nnwIDAQAB\n-----END PUBLIC KEY-----";
                            var encrypt = new JSEncrypt();
                            encrypt.setPublicKey(pubKey);
                            var encrypted = encrypt.encrypt(srcStr);
                            var dstStr = encrypted.toString();
                            if (dstStr.length == 0 || dstStr == "false") {
                                console.log("encrypt key fail!");
                                dstStr = "";
                            }
                            return dstStr;
                        }

      Check: S4n6BrhHXPAJPNYJNisLU08vgN132770fFgsOuhinbnowOEXgNVE5BEUA2weKxOOUs85A/P/8HfbeKcE9z/ID7FVnCOEj87ZeOWbqs8nO6pjz5ZXchQlWancyw89SsttpbaWOwQFkQpyyVT/zzjukwzVpoReiy7xqXsmrGHvXglJOAtK3o6FWW59AzuT/jeca+JOpXG1hA4sKryi3FQPurQJU3f18QSD1IdEGatePmUi+YKLI+ywzKKiLbJJNiK3oFzph+HIGSr6PdwoUVijqTtMKoT9iTcDdbHV+j1riQiuasAolTCiuLYkyNn0h547OsfvUXLvWQw/YBZ0fS4/yA==