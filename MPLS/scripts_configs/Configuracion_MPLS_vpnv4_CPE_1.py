from netmiko import ConnectHandler
from getpass import getpass
import importlib
from configs import from_PE1_to_CPEs
from configs import SW_1
from configs import CPE_1

# Prompt para las credenciales SSH del usuario
# El username es mostrado en texto plano
user = input('Ingrese el Usuario SSH: ')

# El password es escondido al momento de tipear
passwd = getpass('Ingrese la contraseña: ')

routers = [
    {
        "hostname" : "clab-MPLS-CPE-1",
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
    
    #

    #Configuración de CPE_1
    config_cpe_1_interfaces = CPE_1.config_interfaces
    config_cpe_1_routing = CPE_1.config_routing
    #
    
    # Aplicamos configuraciones en CPE_1
    apply_config = conexion.send_config_set(
        config_cpe_1_interfaces
    )

    apply_config = conexion.send_config_set(
        config_cpe_1_routing
    )

    # Cerramos la conexión SSH
    conexion.disconnect()