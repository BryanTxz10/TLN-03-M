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
        "platform" : "vrp"
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
    if router["platform"] == "ios":
        
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
    else:
        device = {
            'device_type': 'huawei',
            'host': router["hostname"],
            'username': user, # usaremos input() para recolectar el usuario
            'password': passwd, # usaremos getpass() para recolectar de manera segura el password
            'session_log': 'R-HUAWEI-log.txt',
        }
        print("#"*60)
        print(f"Conectanddo con Router {router["hostname"]}")
        print("#"*60)
        conexion_vrp = ConnectHandler(**device)
        print("#"*60)
        print(f"Configurando {router["hostname"]}")
        print("#"*60)
        nombre_router_vrp = router["hostname"].split("-")[-1]
        modulo = importlib.import_module(
            f'configs.{nombre_router_vrp}'
        )
    
        output = conexion_vrp.send_config_set(
            modulo.config_interfaces,
            strip_command=False,
            cmd_verify=False, 
            exit_config_mode=False
        )
        output_2 = conexion_vrp.send_config_set(
            modulo.config_igp,
            strip_command=False,
            cmd_verify=False, 
            exit_config_mode=False
        )
        output_3 = conexion_vrp.send_config_set(
            modulo.config_bgp,
            strip_command=False,
            cmd_verify=False, 
            exit_config_mode=False
        )
    
        output_4 = conexion_vrp.send_config_set(
            modulo.config_mpls,
            strip_command=False,
            cmd_verify=False, 
            exit_config_mode=False
        )
        print(f'\nGuardando Configuración')
        commit_ = conexion_vrp.send_command_timing('commit', strip_command=False)
        return_ = conexion_vrp.send_command_timing('return', strip_command=False)
        save_ = conexion_vrp.send_command_timing('save', strip_command=False)
        if 'Y/N' in save_:
            output_2 = conexion_vrp.send_command_timing(
            'Y',
            strip_command=False)
        # Cerramos la conexión SSH
        conexion.disconnect()