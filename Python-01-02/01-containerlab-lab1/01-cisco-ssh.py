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
                  # allow_agent=False,
                   look_for_keys=False #False cuando es un router, True para buscar private keys in ~/.ssh/
                   )

#comando = ['show ver']
comando = "show ver"

stdin, stdout, stderr = ssh_client.exec_command(comando)
time.sleep(.5)
print(stdout.read().decode())

ssh_client.close()