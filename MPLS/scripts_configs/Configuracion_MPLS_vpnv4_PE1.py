from netmiko import ConnectHandler
from getpass import getpass
import importlib
from configs import from_PE1_to_CPEs
from configs import SW_1

# Prompt para las credenciales SSH del usuario
# El username es mostrado en texto plano
user = input('Ingrese el Usuario SSH: ')

# El password es escondido al momento de tipear
passwd = getpass('Ingrese la contraseña: ')

routers = [
    {
        "hostname" : "clab-MPLS-PE1",
        "platform" : "ios"
    }
]

switches = [
    {
        "hostname" : "clab-MPLS-SW-1",
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
    
    # Configuración de PE1 hacia CPE_1
    modulo = from_PE1_to_CPEs.config_vrf
    modulo_2 = from_PE1_to_CPEs.config_int_cpes
    modulo_3 = from_PE1_to_CPEs.config_routing
    #

    # Aplicamos configuraciones en PE1 hacia CPE_1
    output = conexion.send_config_set(
        modulo
    )
    output_2 = conexion.send_config_set(
        modulo_2
    )
    output_3 = conexion.send_config_set(
        modulo_3
    )
    
    # Cerramos la conexión SSH
    conexion.disconnect()

for switch in switches:
        
    device = {
        'device_type': 'cisco_ios',
        'host': switch["hostname"],
        'username': user, # usaremos input() para recolectar el usuario
        'password': passwd, # usaremos getpass() para recolectar de manera segura el password
        'session_log': 'R-SWITCH-log.txt',
    }
    print("#"*60)
    print(f"Conectanddo con Switch {switch["hostname"]}")
    print("#"*60)
    conexion = ConnectHandler(**device)
    print("#"*60)
    print(f"Configurando {switch["hostname"]}")
    print("#"*60)
    
    modulo = SW_1.config_interfaces
        
    output = conexion.send_config_set(
        modulo
    )
        
    # Cerramos la conexión SSH
    conexion.disconnect()