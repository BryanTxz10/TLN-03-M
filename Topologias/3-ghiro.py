import paramiko
import time
 
# =====================================================================
# 1. ATRIBUTOS DE LOS EQUIPOS (DICCIONARIO CONSOLIDADO)
# =====================================================================
equipos = {
    'CPE-BRANCH2': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-BRANCH2',
        'tunnel_id': 1,
        'tunnel_ip': '172.16.10.21',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_hubs': [
            {'nhs_ip': '172.16.10.1', 'nbma_ip': '200.0.0.1', 'multicast': True},
            {'nhs_ip': '172.16.10.2', 'nbma_ip': '190.0.1.1', 'multicast': True}
        ],
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 0,
        'ospf_cost': 10,
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['200.0.2.1', '200.0.0.1', '190.0.1.1', '190.0.0.1', '200.0.1.1', '190.0.2.1'],
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-HQ'
    },
    'CPE-BRANCH2-BK': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2-BK",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-BRANCH2-BK',
        'tunnel_id': 1,
        'tunnel_ip': '172.16.10.22',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_hubs': [
            {'nhs_ip': '172.16.10.1', 'nbma_ip': '200.0.0.1', 'multicast': True},
            {'nhs_ip': '172.16.10.2', 'nbma_ip': '190.0.1.1', 'multicast': True}
        ],
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 0,
        'ospf_cost': 1000,
        'ospf_mtu_ignore': True,          # CORREGIDO: era 'ospfv3_mtu_ignore' (OSPFv6)
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['200.0.0.1', '190.0.1.1', '190.0.0.1', '200.0.1.1', '200.0.2.1', '190.0.2.1'],
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-HQ'
    },
    'CPE-BRANCH': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-BRANCH',
        # --- ATRIBUTOS PARA LIMPIEZA DE TUNEL VIEJO ---
        'cleanup_s2s': {'network': '172.16.10.0', 'wildcard': '0.0.0.3', 'peer': '200.0.0.1'},
 
        'tunnel_id': 1,
        'tunnel_ip': '172.16.10.11',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_hubs': [
            {'nhs_ip': '172.16.10.1', 'nbma_ip': '200.0.0.1', 'multicast': True},
            {'nhs_ip': '172.16.10.2', 'nbma_ip': '190.0.1.1', 'multicast': True}
        ],
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 0,
        'ospf_cost': 10,
        # CORREGIDO: eliminada la key 'ospfv3_mtu_ignore': False (no generaba nada util)
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_lifetime': 1000,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['200.0.0.1', '190.0.1.1', '190.0.0.1', '200.0.1.1', '200.0.2.1', '190.0.2.1'],
        # CORREGIDO: agregado transform-set (faltaba en el original)
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-HQ'
    },
    'CPE-BRANCH-BK': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH-BK",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-BRANCH-BK',
        # --- ATRIBUTOS PARA LIMPIEZA DE TUNEL VIEJO ---
        'cleanup_s2s': {'network': '172.16.20.0', 'wildcard': '0.0.0.3', 'peer': '190.0.1.1'},
 
        'tunnel_id': 1,
        'tunnel_ip': '172.16.10.12',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_hubs': [
            {'nhs_ip': '172.16.10.1', 'nbma_ip': '200.0.0.1', 'multicast': True},
            {'nhs_ip': '172.16.10.2', 'nbma_ip': '190.0.1.1', 'multicast': True}
        ],
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 0,
        'ospf_cost': 1000,
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_lifetime': 1000,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['0.0.0.0'],
        # CORREGIDO: agregado transform-set (faltaba en el original)
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-HQ'
    },
    'CPE-HQ': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-HQ",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-HQ',
        # --- ATRIBUTOS PARA LIMPIEZA DE TUNEL VIEJO ---
        'cleanup_s2s': {'network': '172.16.10.0', 'wildcard': '0.0.0.3', 'peer': '190.0.0.1'},
 
        'tunnel_id': 1,
        'tunnel_description': 'HUB-DMVPN-PRINCIPAL',
        'tunnel_ip': '172.16.10.1',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_redirect': True,
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 255,
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_lifetime': 1000,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['190.0.0.1', '190.0.1.1', '200.0.1.1', '200.0.2.1', '190.0.2.1'],
        # CORREGIDO: agregado transform-set (faltaba en el original)
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-BRANCH'
    },
    'CPE-HQ-BK': {
        "tipo": "CPE",
        "ip_ssh": "clab-ISP-TDP-CLARO-IOL-CPE-HQ-BK",
        "user": "admin", "pass": "admin",
        'hostname': 'CPE-HQ-BK',
        # --- ATRIBUTOS PARA LIMPIEZA DE TUNEL VIEJO ---
        'cleanup_s2s': {'network': '172.16.20.0', 'wildcard': '0.0.0.3', 'peer': '200.0.1.1'},
 
        'tunnel_id': 1,
        'tunnel_description': 'HUB-DMVPN-BACKUP',
        'tunnel_ip': '172.16.10.2',
        'tunnel_mask': '255.255.255.0',
        'tunnel_source': 'Loopback0',
        'tunnel_mode': 'gre multipoint',
        'tunnel_key': 100,
        'ip_redirects': False,
        'ip_mtu': 1400,
        'tcp_adjust_mss': 1360,
        'nhrp_id': 1,
        'nhrp_auth': 'DMVPN123',
        'nhrp_redirect': True,
        'ospf_process': 10,
        'ospf_network_type': 'broadcast',
        'ospf_hello': 5,
        'ospf_dead': 20,
        'ospf_priority': 100,
        'ospf_cost': 100,
        'ospf_networks': [{'network': '172.16.10.0', 'wildcard': '0.0.0.255', 'area': 0}],
        'isakmp_policy_id': 10,
        'isakmp_encryption': 'aes',
        'isakmp_hash': 'sha',
        'isakmp_auth_method': 'pre-share',
        'isakmp_dh_group': 14,
        'isakmp_lifetime': 1000,
        'isakmp_psk': 'TLN03',
        'isakmp_peers': ['200.0.1.1', '200.0.0.1', '190.0.0.1', '200.0.2.1', '190.0.2.1', '190.0.1.1'],
        # CORREGIDO: agregado transform-set (faltaba en el original)
        'ipsec_transform_set_name': 'TS-DMVPN',
        'ipsec_encryption': 'esp-aes',
        'ipsec_authentication': 'esp-sha-hmac',
        'ipsec_mode': 'transport',
        'ipsec_profile': 'PF-TO-BRANCH'
    }
}
 
# =====================================================================
# 2. FUNCIÓN GENERADORA DE CONFIGURACIÓN DMVPN (DINÁMICA)
# =====================================================================
def generar_config_dmvpn(params):
    cmds = [
        "terminal length 0",
        "configure terminal",
        f"hostname {params['hostname']}"
    ]
 
    # --- LIMPIEZA DE TÚNEL SITE-TO-SITE ANTERIOR ---
    if 'cleanup_s2s' in params:
        cln = params['cleanup_s2s']
        cmds.extend([
            f"no interface Tunnel{params['tunnel_id']}",
            f"router ospf {params['ospf_process']}",
            f"no network {cln['network']} {cln['wildcard']} area 0",
            "exit",
            f"no crypto ipsec profile {params['ipsec_profile']}",
            f"no crypto isakmp key {params['isakmp_psk']} address {cln['peer']}",
            f"no crypto isakmp policy {params['isakmp_policy_id']}"
        ])
 
    # --- CONFIGURACIÓN DE TÚNEL NUEVO ---
    cmds.extend([
        f"interface Tunnel{params['tunnel_id']}"
    ])
 
    if 'tunnel_description' in params:
        cmds.append(f"description {params['tunnel_description']}")
 
    cmds.append(f"ip address {params['tunnel_ip']} {params['tunnel_mask']}")
 
    if not params.get('ip_redirects', True):
        cmds.append("no ip redirects")
 
    cmds.extend([
        f"ip mtu {params['ip_mtu']}",
        f"ip nhrp authentication {params['nhrp_auth']}"
    ])
 
    # NHRP para Spokes (Map y NHS)
    if 'nhrp_hubs' in params:
        for hub in params['nhrp_hubs']:
            cmds.append(f"ip nhrp map {hub['nhs_ip']} {hub['nbma_ip']}")
            if hub.get('multicast'):
                cmds.append(f"ip nhrp map multicast {hub['nbma_ip']}")
            cmds.append(f"ip nhrp nhs {hub['nhs_ip']}")
 
    cmds.append(f"ip nhrp network-id {params.get('nhrp_id', 1)}")
 
    # NHRP Redirect para Hubs
    if params.get('nhrp_redirect'):
        cmds.append("ip nhrp redirect")
 
    cmds.extend([
        f"ip tcp adjust-mss {params['tcp_adjust_mss']}",
        f"ip ospf network {params['ospf_network_type']}",
        f"ip ospf dead-interval {params['ospf_dead']}",
        f"ip ospf hello-interval {params['ospf_hello']}",
        f"ip ospf priority {params['ospf_priority']}"
    ])
 
    if 'ospf_cost' in params:
        cmds.append(f"ip ospf cost {params['ospf_cost']}")
 
    # CORREGIDO: key renombrada a 'ospf_mtu_ignore' y comando corregido a
    # 'ip ospf mtu-ignore' (OSPFv2). El original usaba 'ospfv3 mtu-ignore'
    # que corresponde a OSPFv6 y no tiene efecto en el proceso IPv4.
    if params.get('ospf_mtu_ignore'):
        cmds.append("ip ospf mtu-ignore")
 
    cmds.extend([
        f"tunnel source {params['tunnel_source']}",
        f"tunnel mode {params['tunnel_mode']}",
        f"tunnel key {params['tunnel_key']}",
        f"tunnel protection ipsec profile {params['ipsec_profile']}",
        "exit"
    ])
 
    # --- CONFIGURACIÓN DE OSPF ---
    cmds.extend([
        f"router ospf {params['ospf_process']}"
    ])
    for red in params['ospf_networks']:
        cmds.append(f"network {red['network']} {red['wildcard']} area {red['area']}")
    cmds.append("exit")
 
    # --- CONFIGURACIÓN DE SEGURIDAD FASE 1 (ISAKMP) ---
    cmds.extend([
        f"crypto isakmp policy {params['isakmp_policy_id']}",
        f"encryption {params['isakmp_encryption']}",
        f"hash {params['isakmp_hash']}",
        f"authentication {params['isakmp_auth_method']}",
        f"group {params['isakmp_dh_group']}"
    ])
    if 'isakmp_lifetime' in params:
        cmds.append(f"lifetime {params['isakmp_lifetime']}")
    cmds.append("exit")
 
    for peer in params['isakmp_peers']:
        cmds.append(f"crypto isakmp key {params['isakmp_psk']} address {peer}")
 
    # --- CONFIGURACIÓN DE SEGURIDAD FASE 2 (IPSEC) ---
    # CORREGIDO: todos los equipos ahora tienen 'ipsec_transform_set_name'
    # en el diccionario, por lo que este bloque se ejecuta para los 6 CPEs.
    if 'ipsec_transform_set_name' in params:
        cmds.extend([
            f"crypto ipsec transform-set {params['ipsec_transform_set_name']} {params['ipsec_encryption']} {params['ipsec_authentication']}",
            f"mode {params['ipsec_mode']}",
            "exit"
        ])
 
    cmds.extend([
        f"crypto ipsec profile {params['ipsec_profile']}"
    ])
    if 'ipsec_transform_set_name' in params:
        cmds.append(f"set transform-set {params['ipsec_transform_set_name']}")
 
    cmds.extend([
        "exit",
        "end",
        "write memory"
    ])
 
    return cmds
 
# =====================================================================
# 3. FUNCIÓN DE DESPLIEGUE SSH (Vía Paramiko)
# =====================================================================
def desplegar_ssh(ip, user, password, comandos, hostname):
    try:
        print(f"[{hostname}] Iniciando conexión a {ip}...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip, username=user, password=password, look_for_keys=False)
 
        consola = ssh_client.invoke_shell()
        print(f"[{hostname}] Conectado. Desplegando configuración (Avanzando...)")
 
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
        print(f"[{hostname}] ERROR: Falló el despliegue en {ip}. Detalle: {e}\n")
 
# =====================================================================
# 4. BUCLE PRINCIPAL DE EJECUCIÓN
# =====================================================================
if __name__ == "__main__":
    print("=== INICIANDO DESPLIEGUE AUTOMATIZADO DMVPN ===\n")
 
    for nombre_equipo, parametros in equipos.items():
        if parametros["tipo"] == "CPE":
            lista_comandos = generar_config_dmvpn(parametros)
            desplegar_ssh(
                ip=parametros["ip_ssh"],
                user=parametros["user"],
                password=parametros["pass"],
                comandos=lista_comandos,
                hostname=parametros["hostname"]
            )
 
    print("=== TODOS LOS DESPLIEGUES HAN FINALIZADO ===")
 