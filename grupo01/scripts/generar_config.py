from netmiko import ConnectHandler
import csv
import re
import datetime

ROUTERS = [
    "clab-MPLS-PE1", "clab-MPLS-PE2",
    "clab-MPLS-P1",  "clab-MPLS-P2",
    "clab-MPLS-RR1", "clab-MPLS-RR2",
]

CREDS = {
    "device_type": "cisco_ios",
    "username": "admin",
    "password": "admin",
}

def contar_ospf_full(output):
    """Cuenta cuántos vecinos OSPF están en estado FULL."""
    return len(re.findall(r"FULL", output))

def contar_bgp_established(output):
    """Cuenta cuántas filas de la tabla BGP tienen un número en la
    columna State/PfxRcd (significa Established). Si dice 'Idle' o
    'Active' no se cuenta."""
    estados_caidos = ("Idle", "Active", "Connect", "OpenSent", "OpenConfirm")
    total = 0
    for linea in output.splitlines():
        if re.match(r"^\s*\d+\.\d+\.\d+\.\d+", linea):
            if not any(estado in linea for estado in estados_caidos):
                total += 1
    return total

def contar_ldp_neighbors(output):
    """Cuenta cuántos vecinos LDP aparecen (una entrada por 'Peer LDP Ident')."""
    return len(re.findall(r"Peer LDP Ident", output))

def contar_interfaces_activas(output):
    """Cuenta líneas de 'show ip interface brief' en estado up/up.
    Coincide con el dato que pide el enunciado: 'Interfaces activas'."""
    total = 0
    for linea in output.splitlines():
        if re.search(r"\bup\s+up\b", linea, re.IGNORECASE):
            total += 1
    return total

def extraer_version(output):
    """Extrae la línea de versión de IOS (ej: 'Version 17.12.1')."""
    match = re.search(r"Version\s+([\d.]+\w*)", output)
    return match.group(1) if match else "N/A"

# Rol esperado de cada nodo. Los P (core) no tienen BGP VPNv4 directo,
# así que no se les exige peers_bgp_established > 0.
ROLES = {
    "PE1": "PE", "PE2": "PE",
    "P1": "P", "P2": "P",
    "RR1": "RR", "RR2": "RR",
}

def calcular_estado(rol, ospf, bgp, ldp):
    """OK si los contadores son consistentes con el rol del nodo.
    WARNING si falta algo que ese rol sí debería tener."""
    if ospf == 0 or ldp == 0:
        return "WARNING"
    if rol in ("PE", "RR") and bgp == 0:
        return "WARNING"
    return "OK"

rows = []
for host in ROUTERS:
    nombre = host.split("-")[-1]
    device = {**CREDS, "host": host}

    conn = ConnectHandler(**device)

    version_out = conn.send_command("show version")
    ospf_out = conn.send_command("show ip ospf neighbor")
    bgp_out = conn.send_command("show bgp vpnv4 unicast all summary")
    ldp_out = conn.send_command("show mpls ldp neighbor")
    intf_out = conn.send_command("show ip interface brief")

    conn.disconnect()

    rol = ROLES.get(nombre, "?")
    ospf_n = contar_ospf_full(ospf_out)
    bgp_n = contar_bgp_established(bgp_out)
    ldp_n = contar_ldp_neighbors(ldp_out)
    intf_n = contar_interfaces_activas(intf_out)

    rows.append({
        "router": nombre,
        "rol": rol,
        "ios_version": extraer_version(version_out),
        "interfaces_activas": intf_n,
        "vecinos_ospf_full": ospf_n,
        "peers_bgp_established": bgp_n,
        "vecinos_ldp": ldp_n,
        "estado": calcular_estado(rol, ospf_n, bgp_n, ldp_n),
    })

    print(f"{nombre} [{rol}]: IF={intf_n} OSPF={ospf_n} BGP={bgp_n} LDP={ldp_n} "
          f"-> {rows[-1]['estado']}")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
fname = f"reportes/estado_red_{ts}.csv"

campos = ["router", "rol", "ios_version", "interfaces_activas",
          "vecinos_ospf_full", "peers_bgp_established", "vecinos_ldp",
          "estado"]

with open(fname, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=campos)
    writer.writeheader()
    writer.writerows(rows)

print(f"\nCSV generado: {fname}")