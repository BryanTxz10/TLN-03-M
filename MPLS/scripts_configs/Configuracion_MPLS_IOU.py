from netmiko import ConnectHandler
from getpass import getpass
import importlib

# Prompt para las credenciales SSH del usuario
# El username es mostrado en texto plano
user = input('Ingrese el Usuario SSH: ')

# El password es escondido al momento de tipear
passwd = getpass('Ingrese la contraseña: ')

routers = [
    {
        "hostname" : "clab-MPLS-P1",
        "platform" : "ios"
    },
    {
        "hostname" : "clab-MPLS-P2",
        "platform" : "ios"
    },
    {
        "hostname" : "clab-MPLS-PE1",
        "platform" : "ios"
    },
    {
        "hostname" : "clab-MPLS-PE2",
        "platform" : "ios"
    },
    {
        "hostname" : "clab-MPLS-RR1",
        "platform" : "ios"
    },
    {
        "hostname" : "clab-MPLS-RR2",
        "platform" : "ios"
    }
]

for router in routers:
    
    device = {
        'device_type': 'cisco_ios',
        'host': router["hostname"],
        'username': user, # usaremos input() para recolectar el usuario
        'password': passwd, # usaremos getpass() para recolectar de manera segura el password
        'session_log': 'R-CISCO-log.txt',
    }
    print("#"*60)
    print(f"Conectanddo con Router {router["hostname"]}")
    print("#"*60)
    conexion = ConnectHandler(**device)
    print("#"*60)
    print(f"Configurando {router["hostname"]}")
    print("#"*60)
    #print(conexion.send_command('show run int e0/0'))
    nombre_router = router["hostname"].split("-")[-1]
    modulo = importlib.import_module(
        f'configs.{nombre_router}'
    )
    
    output = conexion.send_config_set(
        modulo.config_interfaces
    )
    output_2 = conexion.send_config_set(
        modulo.config_igp
    )
    output_3 = conexion.send_config_set(
        modulo.config_bgp
    )
    
    # Cerramos la conexión SSH
    conexion.disconnect()