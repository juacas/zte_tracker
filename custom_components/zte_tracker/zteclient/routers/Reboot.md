Post to this URL:

/?_type=menuData&_tag=devmgr_restartmgr_lua.lua

PostData:
```javascript
var PostData = "IF_ACTION=Restart&Btn_restart="
var cryptoKey = randomNum(16);
var cryptoIv = randomNum(16);

PostData += "&_sessionTOKEN="+_sessionTmpToken; // IF_ACTION=Restart&Btn_restart=&_sessionTOKEN=e2uhwI2y5UEQsgcfpPw3JHUe

var degistStr = sha256(PostData); // d0adb2368165f25af61dbed05da9f5e5826c88bd7e2c12cf5e16f83717cbd994

selfHeader["Check"] = asyEncode(degistStr); // eurugPTIkXVJ0HdCl5483Xgnw5btc2ki6tp/R949/RAZ3OBUCVIPFRwIXMnWwOVJZxVugL0B7aB+GL2XzH/ikhSYXPa70cI3/kDFeMAigCPvLM8g8g8/qqdqncFAjfqlVwKoGU0qHE+FbfToQqKAADgIH7gfj22GUd/bwi2DUtk6Phtc8wETkd4rs8wPY8LZgySjva6ZCAUCgxXDAeUWiqw6yxS1ZTeFRBD7wvompRGxz7BIEPlmOYuxfyecu9oo9f56M6wlTNDNzBa53CitY7BQ7pcglGl8TzcqJdH17Gb+bo9QhseJeUcJ/i8hjJDdLRHT2sg9Ibyil2wtBiczpg==

$.ajax({
url:ServerAddr,
type: 'POST',
data: PostData,
headers: selfHeader,
processData: true,
async: asyncFlag,
timeout: 30000,
cache:false,
()=>{})

// Use  JSEncrypt v2.3.0 | https://npmcdn.com/jsencrypt@2.3.0/LICENSE.txt */
function asyEncode(srcStr)
{
var pubKey = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAodPTerkUVCYmv28SOfRV\n7UKHVujx/HjCUTAWy9l0L5H0JV0LfDudTdMNPEKloZsNam3YrtEnq6jqMLJV4ASb\n1d6axmIgJ636wyTUS99gj4BKs6bQSTUSE8h/QkUYv4gEIt3saMS0pZpd90y6+B/9\nhZxZE/RKU8e+zgRqp1/762TB7vcjtjOwXRDEL0w71Jk9i8VUQ59MR1Uj5E8X3WIc\nfYSK5RWBkMhfaTRM6ozS9Bqhi40xlSOb3GBxCmliCifOJNLoO9kFoWgAIw5hkSIb\nGH+4Csop9Uy8VvmmB+B3ubFLN35qIa5OG5+SDXn4L7FeAA5lRiGxRi8tsWrtew8w\nnwIDAQAB\n-----END PUBLIC KEY-----";
var encrypt = new JSEncrypt();
encrypt.setPublicKey(pubKey);
var encrypted = encrypt.encrypt(srcStr);
var dstStr = encrypted.toString();
if(dstStr.length == 0 || dstStr == "false")
{
console.log("encrypt key fail!");
dstStr = "";
}
return dstStr;
}
```

Example request:

curl 'https://10.0.0.1/?_type=menuData&_tag=devmgr_restartmgr_lua.lua' \
  -H 'Accept: */*' \
  -H 'Accept-Language: es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6' \
  -H 'Check: SxxmvE01nduN7f3+th4GIiPMeFKxPfOI4kNTZYHmnsZ2FfakTXLwGyAUbhkgeSf0DcGXcHTOBjnlRGadF7fffcDgBf2Tfyir+7dRNeYQY6FRw2+lOVZI/rphsLFC5/A2N73NpaM5RJ0j2nyYGlmz+gq/OHvEmm4jsNETTKQtMVg/zy2UC6BDnSwnzDQ5X5jS9Y7hup3zLE5SW8Uy9CzfXimgKhqcbv7K33PoGtjlwMhTdY+hInUnAstZz14Lo+yhHHUY7ZQPr78O8dzVTYSbbXp4OVgrD9hEcgV3x/fS/FbTJ8EkPsnfAny0LoH2Bih+dIQ/oZnkCRXMTzq+6F+9Vg==' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
  -b '_TESTCOOKIESUPPORT=1; SID_HTTPS_=8127fa8fa8bdd850ed68a5c7c834e9f71c55aaa667397dc1e4df319a49a90132' \
  -H 'DNT: 1' \
  -H 'Origin: http://10.0.0.1' \
  -H 'Referer: http://10.0.0.1/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --data-raw 'IF_ACTION=Restart&Btn_restart=&_sessionTOKEN=K5r7Gq3GPe4CZ6L9sB8wbbgE' \
  --insecure