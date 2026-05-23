#/usr/bin/python3

import paramiko
import time

# =====================================================================
# 1. ATRIBUTOS DE LOS EQUIPOS BACKBONE (PARAMETRIZACIÓN)
# =====================================================================
backbone = {
    "M3": {
        "rol": "PE_BORDE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-M3", # Cambiar por IP real de gestión
        "user": "admin", "pass": "admin",
        "interfaz": "Ethernet1/0",
        "ip_int": "10.0.0.73", "mascara_int": "255.255.255.252",
        "ruta_red": "200.0.2.0", "ruta_mask": "255.255.255.248", "ruta_nh": "10.0.0.74"
        # M3 no lleva tag, por lo que no lo declaramos
    },
    "C5": {
        "rol": "PE_BORDE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-C5", # Cambiar por IP real de gestión
        "user": "admin", "pass": "admin",
        "interfaz": "Ethernet1/2",
        "ip_int": "10.0.0.77", "mascara_int": "255.255.255.252",
        "ruta_red": "190.0.2.0", "ruta_mask": "255.255.255.248", "ruta_nh": "10.0.0.78",
        "ruta_tag": "190"  # Atributo opcional para el tag
    },
    "M2": {
        "rol": "PE_GLOBAL",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-M2", # Cambiar por IP real de gestión
        "user": "admin", "pass": "admin",
        "pl_nombre": "PL-PUB-MOVISTAR",
        "pl_seq": "15",
        "pl_red": "200.0.2.0/29"
    },
    "C2": {
        "rol": "PE_GLOBAL",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-C2", # Cambiar por IP real de gestión
        "user": "admin", "pass": "admin",
        "pl_nombre": "PL-PUB-CLARO",
        "pl_seq": "15",
        "pl_red": "190.0.2.0/29"
    }
}

# =====================================================================
# 2. FUNCIONES GENERADORAS DE CONFIGURACIÓN
# =====================================================================
def generar_config_pe_borde(params):
    """Genera la configuración para los routers que conectan hacia las sedes (M3, C5)"""
    # Base de la ruta estática
    cmd_ruta = f"ip route {params['ruta_red']} {params['ruta_mask']} {params['ruta_nh']}"
    
    # Verificamos si existe el atributo 'ruta_tag' y lo anexamos dinámicamente
    if "ruta_tag" in params:
        cmd_ruta += f" tag {params['ruta_tag']}"

    cmds = [
        "terminal length 0",
        "configure terminal",
        cmd_ruta,
        f"interface {params['interfaz']}",
        f"ip address {params['ip_int']} {params['mascara_int']}",
        "no shutdown",
        "exit",
        "end",
        "write memory"
    ]
    return cmds

def generar_config_pe_global(params):
    """Genera la configuración para los routers que publican hacia Internet (M2, C2)"""
    cmds = [
        "terminal length 0",
        "configure terminal",
        f"ip prefix-list {params['pl_nombre']} seq {params['pl_seq']} permit {params['pl_red']}",
        "end",
        "write memory"
    ]
    return cmds

# =====================================================================
# 3. FUNCIÓN DE DESPLIEGUE SSH
# =====================================================================
def desplegar_ssh(ip, user, password, comandos, hostname):
    try:
        print(f"[{hostname}] Iniciando conexión a {ip}...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip, username=user, password=password, look_for_keys=False)
        
        consola = ssh_client.invoke_shell()
        print(f"[{hostname}] Conectado. Aplicando comandos (Avanzando...)")
        
        time.sleep(1)
        if consola.recv_ready():
            consola.recv(65000)

        for cmd in comandos:
            consola.send(f'{cmd}\n')
            time.sleep(0.1) 
            if consola.recv_ready():
                consola.recv(65000)
                
        time.sleep(2)
        ssh_client.close()
        print(f"[{hostname}] Completado exitosamente.\n")
        
    except Exception as e:
        print(f"[{hostname}] ERROR: Falló el despliegue. Detalle: {e}\n")

# =====================================================================
# 4. BUCLE PRINCIPAL DE EJECUCIÓN
# =====================================================================
print("=== INICIANDO CONFIGURACIÓN DE BACKBONE ===\n")

for router, parametros in backbone.items():
    # Enrutar a la función correcta según su rol en la red
    if parametros["rol"] == "PE_BORDE":
        lista_comandos = generar_config_pe_borde(parametros)
    elif parametros["rol"] == "PE_GLOBAL":
        lista_comandos = generar_config_pe_global(parametros)
        
    desplegar_ssh(
        ip=parametros["ip_ssh"], 
        user=parametros["user"], 
        password=parametros["pass"], 
        comandos=lista_comandos, 
        hostname=router
    )

print("=== TODOS LOS DESPLIEGUES HAN FINALIZADO ===")