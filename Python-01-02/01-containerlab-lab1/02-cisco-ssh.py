#/usr/bin/python3

import paramiko
from getpass import getpass
import time

r1 = "clab-lab-iol-2r-r1"
r2 = "clab-lab-iol-2r-r2"

username = "admin"
password = "admin"

ssh_client = paramiko.SSHClient()
ssh_client.load_system_host_keys()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

ssh_client.connect(hostname=r1,
                   username=username,
                   password=password,
                   look_for_keys=False #False cuando es un router, True para buscar private keys in ~/.ssh/
                   )

ACCESO_DISPOSITIVO = ssh_client.invoke_shell()

ACCESO_DISPOSITIVO.send('term length 0\n')
ACCESO_DISPOSITIVO.send('show ip int br\n')
ACCESO_DISPOSITIVO.send('conf t\n')
ACCESO_DISPOSITIVO.send('int lo0\n')
ACCESO_DISPOSITIVO.send('no sh\n')
ACCESO_DISPOSITIVO.send('end\n')
ACCESO_DISPOSITIVO.send('sh ip ospf nei\n')
time.sleep(3)
output = ACCESO_DISPOSITIVO.recv(65000)
print (output.decode('ascii'))
ssh_client.close()