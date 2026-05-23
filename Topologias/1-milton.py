#/usr/bin/python3

import paramiko
import time

# =====================================================================
# 1. ATRIBUTOS DE LOS EQUIPOS (TOTALMENTE PARAMETRIZADOS)
# =====================================================================
equipos = {
    "CPE-PRINCIPAL": {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2",
        "user": "admin", "pass": "admin",
        "hostname": "CPE-BRANCH2",
        "int_wan": "Ethernet0/1",
        "int_lan": "Ethernet0/2",
        "loopback_ip": "200.0.2.1",
        "wan_ip": "10.0.0.74", "wan_mask": "255.255.255.252",
        "wan_gw": "10.0.0.73",
        "vrrp_prio": "110",
        "ospf_id": "5.5.5.5",
        "nat_pool_start": "200.0.2.2", "nat_pool_end": "200.0.2.6",
        "vlans": [
            {
                "id": "25",
                "ip_subint": "192.168.25.2",  # IP .2 para el Principal
                "ip_vrrp": "192.168.25.1",
                "mask": "255.255.255.0",
                "segmento": "192.168.25.0",
                "wildcard": "0.0.0.255"
            },
            {
                "id": "30",
                "ip_subint": "192.168.30.2",
                "ip_vrrp": "192.168.30.1",
                "mask": "255.255.255.0",
                "segmento": "192.168.30.0",
                "wildcard": "0.0.0.255"
            }
        ]
    },
    
    "CPE-BACKUP": {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2-BK",
        "user": "admin", "pass": "admin",
        "hostname": "CPE-BRANCH2-BK",
        "int_wan": "Ethernet0/1",
        "int_lan": "Ethernet0/2",
        "loopback_ip": "190.0.2.1",
        "wan_ip": "10.0.0.78", "wan_mask": "255.255.255.252",
        "wan_gw": "10.0.0.77",
        "vrrp_prio": "95",             # Prioridad más baja para el Backup
        "ospf_id": "6.6.6.6",
        "nat_pool_start": "190.0.2.2", "nat_pool_end": "190.0.2.6",
        "vlans": [
            {
                "id": "25",
                "ip_subint": "192.168.25.3",  # IP .3 para el Backup
                "ip_vrrp": "192.168.25.1",
                "mask": "255.255.255.0",
                "segmento": "192.168.25.0",
                "wildcard": "0.0.0.255"
            },
            {
                "id": "30",
                "ip_subint": "192.168.30.3",
                "ip_vrrp": "192.168.30.1",
                "mask": "255.255.255.0",
                "segmento": "192.168.30.0",
                "wildcard": "0.0.0.255"
            }
        ]
    },
    
    "SWITCH-SEDE": {
        "tipo": "SW",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-SW-R2-PISO1",
        "user": "admin", "pass": "admin",
        "hostname": "SW-R2-PISO1",
        
        # Puertos que van hacia los routers
        "puertos_troncales": ["Ethernet0/1", "Ethernet0/2"],
        
        # VLANs del switch y los puertos de acceso asignados a cada una
        "vlans": [
            {
                "id": "25",
                "nombre": "VLAN_25",
                "puertos_acceso": ["Ethernet0/3", "Ethernet1/1"]
            },
            {
                "id": "30",
                "nombre": "VLAN_30",
                "puertos_acceso": ["Ethernet1/2", "Ethernet1/3"]
            }
        ]
    }
}

# =====================================================================
# 2. FUNCIONES GENERADORAS DE CONFIGURACIÓN
# =====================================================================
def generar_config_cpe(params):
    cmds = [
        "terminal length 0",
        "configure terminal",
        f"hostname {params['hostname']}",
        
        # 1. IP SLA y Track
        "ip sla 2",
        "icmp-echo 8.8.8.8 source-interface Loopback0",
        "frequency 5",
        "exit",
        "ip sla schedule 2 life forever start-time now",
        "track 200 ip sla 2 reachability",
        "delay down 5 up 10",
        
        # 2. Interfaces Lógicas y Físicas Parametrizadas
        "interface Loopback0",
        f"ip address {params['loopback_ip']} 255.255.255.255",
        "exit",
        
        f"interface {params['int_wan']}",
        f"ip address {params['wan_ip']} {params['wan_mask']}",
        "ip nat outside",
        "no shutdown",
        "exit",
        
        f"interface {params['int_lan']}",
        "no ip address",
        "no shutdown",
        "exit"
    ]
    
    # 3. Subinterfaces y VRRP dinámicos (Ciclo FOR)
    # Primero, extraemos todos los IDs de VLAN para los comandos "vrrp X track Y"
    vlan_ids = [v["id"] for v in params["vlans"]]
    
    for vlan in params["vlans"]:
        cmds.extend([
            f"interface {params['int_lan']}.{vlan['id']}",
            f"encapsulation dot1Q {vlan['id']}",
            f"ip address {vlan['ip_subint']} {vlan['mask']}",
            "ip nat inside",
            f"vrrp {vlan['id']} ip {vlan['ip_vrrp']}",
            f"vrrp {vlan['id']} priority {params['vrrp_prio']}"
        ])
            
        cmds.append(f"vrrp {vlan['id']} track 200 decrement 20")
        cmds.append("exit")
        
    # 4. Enrutamiento (OSPF dinámico)
    cmds.extend([
        "router ospf 10",
        f"router-id {params['ospf_id']}"
    ])
    
    for vlan in params["vlans"]:
        cmds.append(f"passive-interface {params['int_lan']}.{vlan['id']}")
        
    for vlan in params["vlans"]:
        cmds.append(f"network {vlan['segmento']} {vlan['wildcard']} area 0")
        
    cmds.append("exit")
    cmds.append(f"ip route 0.0.0.0 0.0.0.0 {params['wan_gw']}")
    
    # 5. NAT y ACLs dinámicas
    cmds.append("ip access-list standard 10")
    
    secuencia_acl = 10
    for vlan in params["vlans"]:
        cmds.append(f"{secuencia_acl} permit {vlan['segmento']} {vlan['wildcard']}")
        secuencia_acl += 10
        
    cmds.extend([
        "exit",
        f"ip nat pool BRANCH-POOL {params['nat_pool_start']} {params['nat_pool_end']} prefix-length 29",
        "ip nat inside source list 10 pool BRANCH-POOL overload",
        "end",
        "write memory"
    ])
    
    return cmds


def generar_config_sw(params):
    """Genera la lista de comandos para el Switch de forma dinámica."""
    cmds = [
        "terminal length 0",
        "configure terminal",
        f"hostname {params['hostname']}"
    ]
    
    # 1. Creación dinámica de VLANs
    for vlan in params["vlans"]:
        cmds.extend([
            f"vlan {vlan['id']}",
            f"name {vlan['nombre']}",
            "exit"
        ])
    
    # Preparamos el texto con todas las VLANs permitidas (ej. "25,30")
    vlan_ids_str = ",".join([v["id"] for v in params["vlans"]])
    
    # 2. Interfaces Troncales dinámicas
    for puerto in params["puertos_troncales"]:
        cmds.extend([
            f"interface {puerto}",
            "switchport trunk encapsulation dot1q",
            "switchport mode trunk",
            f"switchport trunk allowed vlan {vlan_ids_str}",
            "no shutdown",
            "exit"
        ])
        
    # 3. Interfaces de Acceso dinámicas
    for vlan in params["vlans"]:
        for puerto in vlan["puertos_acceso"]:
            cmds.extend([
                f"interface {puerto}",
                "switchport mode access",
                f"switchport access vlan {vlan['id']}",
                "no shutdown",
                "exit"
            ])
            
    cmds.extend([
        "end",
        "write memory"
    ])
    
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
        print(f"[{hostname}] Conectado. Desplegando configuración (Avanzando...)")
        
        # Pequeña pausa para limpiar mensajes de bienvenida del router
        time.sleep(1)
        if consola.recv_ready():
            consola.recv(65000)

        for cmd in comandos:
            consola.send(f'{cmd}\n')
            time.sleep(0.1) # Pausa mínima para no saturar
            
            # Vaciamos el buffer silenciosamente para evitar que se desborde
            if consola.recv_ready():
                consola.recv(65000)
                
        # Esperar un poco extra al final para el "write memory"
        time.sleep(2)
        ssh_client.close()
        print(f"[{hostname}] Completado exitosamente.\n")
        
    except Exception as e:
        print(f"[{hostname}] ERROR: Falló el despliegue en {ip}. Detalle: {e}\n")


# =====================================================================
# 4. BUCLE PRINCIPAL DE EJECUCIÓN
# =====================================================================
print("=== INICIANDO DESPLIEGUE AUTOMATIZADO ===\n")

for nombre_equipo, parametros in equipos.items():
    # Identificar qué tipo de equipo es para generar la configuración correcta
    if parametros["tipo"] == "CPE":
        lista_comandos = generar_config_cpe(parametros)
    elif parametros["tipo"] == "SW":
        lista_comandos = generar_config_sw(parametros)
    
    # Enviar la configuración generada vía SSH
    desplegar_ssh(
        ip=parametros["ip_ssh"], 
        user=parametros["user"], 
        password=parametros["pass"], 
        comandos=lista_comandos, 
        hostname=parametros["hostname"]
    )

print("=== TODOS LOS DESPLIEGUES HAN FINALIZADO ===")