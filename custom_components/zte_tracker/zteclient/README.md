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