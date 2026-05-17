#!/usr/bin/python3
import paramiko
import time
from getpass import getpass

host = "192.168.3.1"
username = "ajanampa"
password = getpass("Ingrese el password: ")

cliente = paramiko.SSHClient()

cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy)

cliente.connect(hostname=host,
                username=username,
                password=password)

comandos = ['echo $PATH', 'echo $HOME', 'hostname', 'Telecomunicaciones_xD']

for comando in comandos:
    print(f"{'#'*10} Ejecutando el comando : {comando} {'#'*10}")
    stdin, stdout, stderr = cliente.exec_command(comando)
    time.sleep(.5)
    print(stdout.read().decode())
    error = stderr.read().decode()
    if error:
            print(error)

cliente.close()