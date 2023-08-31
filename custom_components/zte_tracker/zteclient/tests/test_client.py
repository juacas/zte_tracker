import unittest
import os
from zte_client import zteClient
#import ...

#class zteClientTest(unittest.TestCase):
password = os.environ.get('TEST_PASSWORD', '!secret')
host = os.environ.get('TEST_HOST', 'xx192.168.3.1')
user = os.environ.get('TEST_USER', 'user')
model = os.environ.get('TEST_MODEL', 'F6640')

# Check zteClient.get_models() returns a list.

models = zteClient.get_models(None)
print(models)

client = zteClient(host, user, password, model)
res = client.login()
if res:
    devices = client.get_devices_response()
    i = 1
    for device in devices:
        if device.get('Active', False) == True:
            name = device.get('HostName', 'Desconocido')
            mac = device.get('MACAddress', 'MAC??')
            if name is not None:
                name = name.replace('未知设备', 'Desconocido')
            print(f"{i}) {mac} {name} {device.get('NetworkType')}")
            i+=1
else:
    print("Error: {0}".format(client.statusmsg));
client.logout()
