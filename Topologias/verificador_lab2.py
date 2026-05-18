#!/usr/bin/env python3
"""
================================================================================
  LABORATORIO 2 - SISTEMA DE VERIFICACIÓN AUTOMATIZADA
  Fase 4 | Validación de Topología DMVPN Branch2
  Herramienta: Paramiko (exec_command + invoke_shell)
================================================================================
  Dispositivos objetivo según pc2.md:
    - CPE-BRANCH2      (172.20.20.26)
    - CPE-BRANCH2-BK   (172.20.20.17)
  Verificación extendida (contexto completo):
    - CPE-HQ           (172.20.20.10)
    - CPE-HQ-BK        (172.20.20.XX) → derivado del yml
    - CPE-BRANCH       (172.20.20.36)
    - CPE-BRANCH-BK    (172.20.20.35)
================================================================================
"""

import paramiko
import time
import sys
import os
import json
import datetime
import re
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# COLORES ANSI (compatibles Windows con colorama o directamente en terminal)
# ──────────────────────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
except ImportError:
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = BLUE = MAGENTA = ""

# ──────────────────────────────────────────────────────────────────────────────
# INVENTARIO DE DISPOSITIVOS
# Fuente: archivos .partial (campo Ethernet0/0 / clab-mgmt)
# ──────────────────────────────────────────────────────────────────────────────
DEVICES = {
    "CPE-HQ": {
        "host":     "172.20.20.10",
        "username": "admin",
        "password": "admin",
        "role":     "HUB-PRIMARY",
        "tunnel_ip":"172.16.10.1",
        "loopback": "200.0.0.1",
        "lans":     ["192.168.10.0/24", "192.168.20.0/24"],
    },
    "CPE-HQ-BK": {
        "host":     "172.20.20.11",   # ajustar si difiere
        "username": "admin",
        "password": "admin",
        "role":     "HUB-BACKUP",
        "tunnel_ip":"172.16.10.2",
        "loopback": "190.0.1.1",
        "lans":     ["192.168.10.0/24", "192.168.20.0/24"],
    },
    "CPE-BRANCH": {
        "host":     "172.20.20.36",
        "username": "admin",
        "password": "admin",
        "role":     "SPOKE-BRANCH1-PRIMARY",
        "tunnel_ip":"172.16.10.11",
        "loopback": "190.0.0.1",
        "lans":     ["192.168.5.0/24", "192.168.15.0/24"],
    },
    "CPE-BRANCH-BK": {
        "host":     "172.20.20.35",
        "username": "admin",
        "password": "admin",
        "role":     "SPOKE-BRANCH1-BACKUP",
        "tunnel_ip":"172.16.10.12",
        "loopback": "200.0.1.1",
        "lans":     ["192.168.5.0/24", "192.168.15.0/24"],
    },
    # ─── NUEVOS (Branch2) ─────────────────────────────────────────────────
    "CPE-BRANCH2": {
        "host":     "172.20.20.26",
        "username": "admin",
        "password": "admin",
        "role":     "SPOKE-BRANCH2-PRIMARY",
        "tunnel_ip":"172.16.10.21",
        "loopback": "200.0.2.1",
        "lans":     ["192.168.25.0/24", "192.168.30.0/24"],
    },
    "CPE-BRANCH2-BK": {
        "host":     "172.20.20.17",
        "username": "admin",
        "password": "admin",
        "role":     "SPOKE-BRANCH2-BACKUP",
        "tunnel_ip":"172.16.10.22",
        "loopback": "190.0.2.1",
        "lans":     ["192.168.25.0/24", "192.168.30.0/24"],
    },
}

# Dispositivos primarios Branch2 (foco del pc2.md)
BRANCH2_DEVICES = ["CPE-BRANCH2", "CPE-BRANCH2-BK"]

# Resultados globales para reporte final
RESULTS: dict = {}
LOG_LINES: list = []

# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────

def log(msg: str):
    """Registra en pantalla y en buffer de log."""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    LOG_LINES.append(line)
    print(line)


def banner(title: str, width: int = 70, char: str = "═"):
    line = char * width
    padding = (width - len(title) - 2) // 2
    print(f"\n{BOLD}{CYAN}{line}{RESET}")
    print(f"{BOLD}{CYAN}{'':>{padding}} {title} {'':>{padding}}{RESET}")
    print(f"{BOLD}{CYAN}{line}{RESET}\n")


def section(title: str):
    print(f"\n{BOLD}{YELLOW}── {title} {'─' * (60 - len(title))}{RESET}")


def ok(msg: str):
    log(f"  {GREEN}[✓] {msg}{RESET}")


def fail(msg: str):
    log(f"  {RED}[✗] {msg}{RESET}")


def warn(msg: str):
    log(f"  {YELLOW}[!] {msg}{RESET}")


def info(msg: str):
    log(f"  {BLUE}[i] {msg}{RESET}")


# ──────────────────────────────────────────────────────────────────────────────
# CONEXIÓN SSH con Paramiko
# ──────────────────────────────────────────────────────────────────────────────

def get_ssh_client(device_name: str) -> Optional[paramiko.SSHClient]:
    """Crea y retorna un cliente SSH conectado al dispositivo."""
    dev = DEVICES[device_name]
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=dev["host"],
            username=dev["username"],
            password=dev["password"],
            look_for_keys=False,
            timeout=10,
            allow_agent=False,
        )
        ok(f"SSH conectado → {device_name} ({dev['host']})")
        return client
    except Exception as e:
        fail(f"No se pudo conectar a {device_name} ({dev['host']}): {e}")
        return None


def exec_cmd(client: paramiko.SSHClient, command: str, timeout: int = 15) -> str:
    """Ejecuta un comando usando exec_command() y retorna el output."""
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode("utf-8", errors="replace")
        return output
    except Exception as e:
        return f"ERROR: {e}"


def shell_cmds(client: paramiko.SSHClient, commands: list, wait: float = 2.0) -> str:
    """Envía comandos interactivos usando invoke_shell() — para config/verificación."""
    try:
        shell = client.invoke_shell()
        time.sleep(1)
        shell.send("terminal length 0\n")
        time.sleep(0.5)
        # Limpiar buffer inicial
        if shell.recv_ready():
            shell.recv(65535)
        full_output = ""
        for cmd in commands:
            shell.send(cmd + "\n")
            time.sleep(wait)
            if shell.recv_ready():
                chunk = shell.recv(65535).decode("utf-8", errors="replace")
                full_output += chunk
        return full_output
    except Exception as e:
        return f"ERROR: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 1 – VERIFICAR TÚNEL DMVPN
# ──────────────────────────────────────────────────────────────────────────────

def verify_dmvpn(device_name: str) -> dict:
    """
    Verifica estado DMVPN:
      - show dmvpn
      - show interface tunnel1
      - show ip nhrp
    Usa exec_command() según pc2.md Parte 4.
    """
    section(f"DMVPN → {device_name}")
    result = {"device": device_name, "dmvpn_up": False, "nhrp_entries": 0,
              "tunnel_up": False, "peers": [], "raw": {}}

    client = get_ssh_client(device_name)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        # ── show dmvpn ──────────────────────────────────────────────────────
        dmvpn_out = exec_cmd(client, "show dmvpn")
        result["raw"]["show_dmvpn"] = dmvpn_out
        info(f"show dmvpn output ({device_name}):")
        print(f"{dmvpn_out[:800]}")

        # Parsear peers NHRP/DMVPN
        peers = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+\w+\s+(\w+)', dmvpn_out)
        if peers:
            result["peers"] = peers
            result["dmvpn_up"] = True
            ok(f"DMVPN activo – {len(peers)} peer(s) encontrados")
        else:
            # Verificar al menos que el proceso existe
            if "Ident" in dmvpn_out or "nhrp" in dmvpn_out.lower():
                warn(f"DMVPN configurado pero sin peers activos aún")
                result["dmvpn_up"] = True  # proceso existe
            else:
                fail(f"DMVPN no encontrado o sin información")

        # ── show interface tunnel1 ───────────────────────────────────────────
        tun_out = exec_cmd(client, "show interface tunnel1")
        result["raw"]["show_interface_tunnel"] = tun_out
        if "line protocol is up" in tun_out.lower():
            result["tunnel_up"] = True
            ok(f"Tunnel1 → UP/UP")
        elif "line protocol is down" in tun_out.lower():
            fail(f"Tunnel1 → DOWN")
        else:
            warn(f"Estado de Tunnel1 indeterminado")

        # ── show ip nhrp ─────────────────────────────────────────────────────
        nhrp_out = exec_cmd(client, "show ip nhrp")
        result["raw"]["show_ip_nhrp"] = nhrp_out
        nhrp_entries = len(re.findall(r'via\s+\d+\.\d+\.\d+\.\d+', nhrp_out))
        result["nhrp_entries"] = nhrp_entries
        if nhrp_entries > 0:
            ok(f"NHRP: {nhrp_entries} entrada(s) registrada(s)")
        else:
            warn(f"NHRP: sin entradas activas")

        # ── show ip nhrp nhs ─────────────────────────────────────────────────
        nhs_out = exec_cmd(client, "show ip nhrp nhs")
        result["raw"]["show_ip_nhrp_nhs"] = nhs_out
        if "200.0.0.1" in nhs_out or "190.0.1.1" in nhs_out:
            ok(f"NHS registrados correctamente (HUB principal y backup)")
        else:
            warn(f"NHS no encontrados en tabla NHRP")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 2 – VERIFICAR OSPF
# ──────────────────────────────────────────────────────────────────────────────

def verify_ospf(device_name: str) -> dict:
    """
    Verifica estado OSPF:
      - show ip ospf neighbor
      - show ip ospf interface tunnel1
    Nota: pc2.md menciona EIGRP pero la config real usa OSPF área 0.
    """
    section(f"OSPF → {device_name}")
    result = {"device": device_name, "neighbors": [], "ospf_up": False, "raw": {}}

    client = get_ssh_client(device_name)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        # ── show ip ospf neighbor ────────────────────────────────────────────
        ospf_out = exec_cmd(client, "show ip ospf neighbor")
        result["raw"]["ospf_neighbors"] = ospf_out
        info(f"OSPF Neighbors ({device_name}):")
        print(f"{ospf_out[:600]}")

        # Parsear vecinos en estado FULL
        full_neighbors = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+FULL', ospf_out)
        result["neighbors"] = full_neighbors
        if full_neighbors:
            result["ospf_up"] = True
            ok(f"OSPF: {len(full_neighbors)} vecino(s) en estado FULL → {full_neighbors}")
        else:
            # Verificar 2-WAY o INIT también
            any_neighbor = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\w+)', ospf_out)
            if any_neighbor:
                warn(f"OSPF: vecinos presentes pero no en FULL → {any_neighbor}")
            else:
                fail(f"OSPF: sin vecinos detectados")

        # ── show ip ospf interface tunnel1 ───────────────────────────────────
        ospf_int_out = exec_cmd(client, "show ip ospf interface tunnel1")
        result["raw"]["ospf_interface"] = ospf_int_out
        if "area 0" in ospf_int_out.lower():
            ok(f"OSPF: Tunnel1 participando en área 0")
        if "network type broadcast" in ospf_int_out.lower():
            ok(f"OSPF: Tipo de red BROADCAST configurado correctamente")

        # ── show ip ospf ─────────────────────────────────────────────────────
        ospf_proc = exec_cmd(client, "show ip ospf")
        result["raw"]["ospf_process"] = ospf_proc
        if "router id" in ospf_proc.lower():
            rid = re.search(r'Router ID\s+(\d+\.\d+\.\d+\.\d+)', ospf_proc, re.IGNORECASE)
            if rid:
                ok(f"OSPF Router-ID: {rid.group(1)}")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 3 – VERIFICAR TABLA DE RUTAS
# ──────────────────────────────────────────────────────────────────────────────

def verify_routes(device_name: str) -> dict:
    """
    Verifica tabla de rutas:
      - show ip route
      - Valida presencia de rutas hacia LANs de HQ, Branch1 y Branch2
    """
    section(f"RUTAS → {device_name}")
    result = {"device": device_name, "routes_ok": [], "routes_missing": [], "raw": {}}

    # Rutas que deben existir en los spokes de Branch2
    expected_networks = [
        "192.168.10.0",  # LAN HQ VLAN10
        "192.168.20.0",  # LAN HQ VLAN20
        "192.168.5.0",   # LAN Branch1 VLAN5
        "192.168.15.0",  # LAN Branch1 VLAN15
        "172.16.10.0",   # Red tunnel DMVPN
    ]

    client = get_ssh_client(device_name)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        route_out = exec_cmd(client, "show ip route")
        result["raw"]["show_ip_route"] = route_out

        info(f"Tabla de rutas ({device_name}) — fragmento:")
        # Mostrar solo las rutas O (OSPF) y C (connected)
        for line in route_out.splitlines():
            if line.strip().startswith(("O", "C", "S", "B")):
                print(f"  {line}")

        for net in expected_networks:
            if net in route_out:
                result["routes_ok"].append(net)
                ok(f"Ruta encontrada: {net}")
            else:
                result["routes_missing"].append(net)
                warn(f"Ruta NO encontrada: {net}")

        # Verificar default route
        if "0.0.0.0/0" in route_out or "0.0.0.0 0.0.0.0" in route_out:
            ok(f"Default route (0.0.0.0/0) presente")
        else:
            warn(f"Default route no encontrada")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 4 – VERIFICAR VRRP
# ──────────────────────────────────────────────────────────────────────────────

def verify_vrrp(device_name: str) -> dict:
    """
    Verifica estado VRRP:
      - show vrrp brief
      - Valida grupos 25 y 30 (Branch2) o 5 y 15 (Branch1) o 10 y 20 (HQ)
    """
    section(f"VRRP → {device_name}")
    result = {"device": device_name, "vrrp_groups": [], "master_groups": [], "raw": {}}

    dev = DEVICES[device_name]
    # Determinar grupos esperados según rol
    if "BRANCH2" in device_name:
        expected_groups = [25, 30]
    elif "BRANCH" in device_name:
        expected_groups = [5, 15]
    else:
        expected_groups = [10, 20]

    client = get_ssh_client(device_name)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        vrrp_out = exec_cmd(client, "show vrrp brief")
        result["raw"]["show_vrrp_brief"] = vrrp_out
        info(f"VRRP ({device_name}):")
        print(f"{vrrp_out}")

        # Parsear grupos y estado
        for grp in expected_groups:
            if str(grp) in vrrp_out:
                result["vrrp_groups"].append(grp)
                if "Master" in vrrp_out or "Active" in vrrp_out:
                    if re.search(rf'\b{grp}\b.*Master', vrrp_out) or re.search(rf'\b{grp}\b.*Active', vrrp_out):
                        result["master_groups"].append(grp)
                        ok(f"VRRP grupo {grp} → MASTER")
                    else:
                        ok(f"VRRP grupo {grp} → BACKUP (activo)")
                else:
                    ok(f"VRRP grupo {grp} → presente")
            else:
                fail(f"VRRP grupo {grp} NO encontrado")

        # Verificar IPs virtuales
        vrrp_detail = exec_cmd(client, "show vrrp")
        result["raw"]["show_vrrp"] = vrrp_detail
        if "BRANCH2" in device_name:
            for vip in ["192.168.25.1", "192.168.30.1"]:
                if vip in vrrp_detail:
                    ok(f"Virtual IP {vip} configurada")
                else:
                    fail(f"Virtual IP {vip} NO encontrada")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 5 – VERIFICAR NAT
# ──────────────────────────────────────────────────────────────────────────────

def verify_nat(device_name: str) -> dict:
    """
    Verifica NAT overload:
      - show ip nat translations
      - show ip nat statistics
    """
    section(f"NAT → {device_name}")
    result = {"device": device_name, "nat_active": False, "translations": 0, "raw": {}}

    client = get_ssh_client(device_name)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        nat_stats = exec_cmd(client, "show ip nat statistics")
        result["raw"]["nat_statistics"] = nat_stats
        info(f"NAT Statistics ({device_name}):")
        print(f"{nat_stats[:500]}")

        if "outside" in nat_stats.lower() and "inside" in nat_stats.lower():
            result["nat_active"] = True
            ok(f"NAT configurado (inside/outside interfaces detectadas)")

        # Hits de NAT
        hits = re.search(r'Total\s+active\s+translations:\s+(\d+)', nat_stats, re.IGNORECASE)
        if hits:
            ok(f"NAT traducciones activas: {hits.group(1)}")

        nat_trans = exec_cmd(client, "show ip nat translations")
        result["raw"]["nat_translations"] = nat_trans
        trans_count = len([l for l in nat_trans.splitlines() if "---" not in l and l.strip()])
        result["translations"] = trans_count
        if trans_count > 0:
            ok(f"NAT: {trans_count} traducción(es) en tabla")
        else:
            info(f"NAT: tabla vacía (normal si no hay tráfico activo)")

        # Verificar pool correcto para Branch2
        if "BRANCH2" in device_name:
            pool_out = exec_cmd(client, "show ip nat pool")
            result["raw"]["nat_pool"] = pool_out
            if "200.0.2" in pool_out:
                ok(f"NAT Pool Branch2 (200.0.2.x) presente")
            else:
                warn(f"NAT Pool Branch2 no encontrado")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 6 – VERIFICAR CONECTIVIDAD (PING / TRACEROUTE)
# ──────────────────────────────────────────────────────────────────────────────

def verify_connectivity(source_device: str) -> dict:
    """
    Verifica conectividad extremo a extremo desde Branch2:
      - Ping hacia HUB (tunnel)
      - Ping hacia HQ LAN
      - Ping hacia Branch1 LAN
      - Traceroute hacia HQ
    Usa exec_command() con comandos ping extendido de Cisco.
    """
    section(f"CONECTIVIDAD → desde {source_device}")
    result = {"device": source_device, "ping_results": {}, "raw": {}}

    ping_targets = {
        "HUB-Principal (tunnel)":    "172.16.10.1",
        "HUB-Backup (tunnel)":       "172.16.10.2",
        "Branch1 (tunnel)":          "172.16.10.11",
        "HQ LAN VLAN10":             "192.168.10.1",
        "HQ LAN VLAN20":             "192.168.20.1",
        "Branch1 LAN VLAN5":         "192.168.5.1",
        "Branch1 LAN VLAN15":        "192.168.15.1",
        "Internet (8.8.8.8)":        "8.8.8.8",
    }

    client = get_ssh_client(source_device)
    if not client:
        result["error"] = "Sin conexión SSH"
        return result

    try:
        for label, target_ip in ping_targets.items():
            # Ping desde loopback para salir por el túnel
            ping_cmd = f"ping {target_ip} repeat 5 source loopback0"
            ping_out = exec_cmd(client, ping_cmd, timeout=20)
            result["raw"][f"ping_{target_ip}"] = ping_out

            # Parsear success rate
            success = re.search(r'Success rate is (\d+) percent', ping_out)
            if success:
                rate = int(success.group(1))
                result["ping_results"][label] = rate
                if rate == 100:
                    ok(f"PING {label} ({target_ip}) → {rate}% éxito")
                elif rate > 0:
                    warn(f"PING {label} ({target_ip}) → {rate}% éxito (pérdida parcial)")
                else:
                    fail(f"PING {label} ({target_ip}) → FALLO (0%)")
            else:
                warn(f"PING {label} ({target_ip}) → sin respuesta parse")
                result["ping_results"][label] = -1

        # Traceroute hacia HQ
        info(f"Traceroute hacia HQ (192.168.10.1)...")
        trace_out = exec_cmd(client, "traceroute 192.168.10.1 source loopback0 probe 2", timeout=30)
        result["raw"]["traceroute_hq"] = trace_out
        info(f"Traceroute:\n{trace_out[:400]}")

    finally:
        client.close()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 7 – VALIDACIÓN COMPLETA (TODAS LAS VERIFICACIONES)
# ──────────────────────────────────────────────────────────────────────────────

def run_full_validation(target_devices: list = None) -> dict:
    """
    Ejecuta todas las validaciones sobre los dispositivos indicados.
    Por defecto ejecuta sobre CPE-BRANCH2 y CPE-BRANCH2-BK (foco pc2.md).
    """
    if target_devices is None:
        target_devices = BRANCH2_DEVICES

    banner("VALIDACIÓN COMPLETA – LABORATORIO 2")
    all_results = {}

    for dev in target_devices:
        banner(f"DISPOSITIVO: {dev}", char="─")
        dev_results = {}

        dev_results["dmvpn"]        = verify_dmvpn(dev)
        dev_results["ospf"]         = verify_ospf(dev)
        dev_results["routes"]       = verify_routes(dev)
        dev_results["vrrp"]         = verify_vrrp(dev)
        dev_results["nat"]          = verify_nat(dev)
        dev_results["connectivity"] = verify_connectivity(dev)

        all_results[dev] = dev_results

    return all_results


# ──────────────────────────────────────────────────────────────────────────────
# REPORTE FINAL
# ──────────────────────────────────────────────────────────────────────────────

def print_summary(all_results: dict):
    """Imprime resumen visual de resultados."""
    banner("RESUMEN DE VALIDACIONES")

    total_checks = 0
    passed_checks = 0

    for dev_name, modules in all_results.items():
        section(f"Dispositivo: {dev_name}")

        # DMVPN
        dmvpn = modules.get("dmvpn", {})
        if dmvpn.get("tunnel_up"):
            ok(f"Tunnel1: UP");  passed_checks += 1
        else:
            fail(f"Tunnel1: DOWN o no verificado")
        total_checks += 1

        if dmvpn.get("dmvpn_up"):
            ok(f"DMVPN: activo ({len(dmvpn.get('peers',[]))} peers)")
            passed_checks += 1
        else:
            fail(f"DMVPN: sin peers activos")
        total_checks += 1

        # OSPF
        ospf = modules.get("ospf", {})
        if ospf.get("ospf_up"):
            ok(f"OSPF: {len(ospf.get('neighbors',[]))} vecino(s) FULL")
            passed_checks += 1
        else:
            fail(f"OSPF: sin vecinos en FULL")
        total_checks += 1

        # Rutas
        routes = modules.get("routes", {})
        ok_routes   = len(routes.get("routes_ok", []))
        miss_routes = len(routes.get("routes_missing", []))
        if miss_routes == 0:
            ok(f"RUTAS: todas las rutas esperadas presentes ({ok_routes})")
            passed_checks += 1
        else:
            warn(f"RUTAS: {ok_routes} presentes, {miss_routes} faltantes")
        total_checks += 1

        # VRRP
        vrrp = modules.get("vrrp", {})
        if vrrp.get("vrrp_groups"):
            ok(f"VRRP: grupos {vrrp['vrrp_groups']} activos")
            passed_checks += 1
        else:
            fail(f"VRRP: sin grupos detectados")
        total_checks += 1

        # NAT
        nat = modules.get("nat", {})
        if nat.get("nat_active"):
            ok(f"NAT: configurado y activo")
            passed_checks += 1
        else:
            warn(f"NAT: no confirmado")
        total_checks += 1

        # Conectividad
        conn = modules.get("connectivity", {})
        ping_results = conn.get("ping_results", {})
        success_pings = sum(1 for v in ping_results.values() if v > 0)
        total_pings   = len(ping_results)
        if total_pings > 0:
            if success_pings == total_pings:
                ok(f"CONECTIVIDAD: {success_pings}/{total_pings} destinos alcanzables")
                passed_checks += 1
            else:
                warn(f"CONECTIVIDAD: {success_pings}/{total_pings} destinos alcanzables")
                passed_checks += 0.5
        total_checks += 1

    # Score final
    pct = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    print()
    print(f"{BOLD}{'═'*60}{RESET}")
    score_color = GREEN if pct >= 80 else (YELLOW if pct >= 50 else RED)
    print(f"{BOLD}{score_color}  RESULTADO: {passed_checks:.1f}/{total_checks} validaciones — {pct:.1f}%{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}\n")


def save_report(all_results: dict):
    """Guarda reporte en archivo JSON y log .txt."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON (sin raw para legibilidad)
    clean_results = {}
    for dev, mods in all_results.items():
        clean_results[dev] = {}
        for mod, data in mods.items():
            clean_copy = {k: v for k, v in data.items() if k != "raw"}
            clean_results[dev][mod] = clean_copy

    json_file = f"reporte_lab2_{ts}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2, ensure_ascii=False)
    ok(f"Reporte JSON guardado: {json_file}")

    # Log .txt
    log_file = f"log_lab2_{ts}.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"LABORATORIO 2 – LOG DE VERIFICACIÓN\n")
        f.write(f"Fecha: {datetime.datetime.now()}\n")
        f.write("=" * 70 + "\n\n")
        for line in LOG_LINES:
            # Limpiar códigos ANSI para el archivo
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            f.write(clean_line + "\n")
    ok(f"Log guardado: {log_file}")


# ──────────────────────────────────────────────────────────────────────────────
# MENÚ INTERACTIVO
# ──────────────────────────────────────────────────────────────────────────────

def select_devices() -> list:
    """Permite al usuario elegir qué dispositivos verificar."""
    print(f"\n{BOLD}Dispositivos disponibles:{RESET}")
    dev_list = list(DEVICES.keys())
    for i, d in enumerate(dev_list, 1):
        role = DEVICES[d]["role"]
        host = DEVICES[d]["host"]
        tag = f"{GREEN}[NUEVO]{RESET}" if "BRANCH2" in d else ""
        print(f"  [{i}] {d:<20} {host:<15} {role} {tag}")
    print(f"  [A] Todos los dispositivos")
    print(f"  [B] Solo Branch2 (CPE-BRANCH2 + CPE-BRANCH2-BK) [por defecto]")

    choice = input(f"\n{BOLD}Selección (número, A o B): {RESET}").strip().upper()
    if choice == "A":
        return dev_list
    elif choice == "B" or choice == "":
        return BRANCH2_DEVICES
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(dev_list):
                return [dev_list[idx]]
        except ValueError:
            pass
    return BRANCH2_DEVICES


def main_menu():
    """Menú principal interactivo."""
    last_results = {}

    while True:
        banner("LABORATORIO 2 – VERIFICADOR AUTOMATIZADO", char="═")
        print(f"  {CYAN}Topología: DMVPN Branch2 (CPE-BRANCH2 / CPE-BRANCH2-BK){RESET}")
        print(f"  {CYAN}Protocolo de routing: OSPF área 0 | IPsec DMVPN | VRRP | NAT{RESET}\n")

        print(f"  {BOLD}[1]{RESET} Verificar Túnel DMVPN")
        print(f"  {BOLD}[2]{RESET} Verificar OSPF (vecindades)")
        print(f"  {BOLD}[3]{RESET} Verificar Tabla de Rutas")
        print(f"  {BOLD}[4]{RESET} Verificar VRRP")
        print(f"  {BOLD}[5]{RESET} Verificar NAT")
        print(f"  {BOLD}[6]{RESET} Verificar Conectividad (Ping / Traceroute)")
        print(f"  {BOLD}{GREEN}[7]{RESET} Ejecutar Validación Completa")
        print(f"  {BOLD}[8]{RESET} Ver Resumen de Últimos Resultados")
        print(f"  {BOLD}[9]{RESET} Guardar Reporte (JSON + Log)")
        print(f"  {BOLD}[0]{RESET} Salir\n")

        choice = input(f"{BOLD}  Opción: {RESET}").strip()

        if choice == "0":
            print(f"\n{CYAN}  Saliendo... ¡hasta pronto!{RESET}\n")
            break

        elif choice in ("1", "2", "3", "4", "5", "6"):
            devices = select_devices()
            results = {}
            for dev in devices:
                if choice == "1":
                    results[dev] = verify_dmvpn(dev)
                elif choice == "2":
                    results[dev] = verify_ospf(dev)
                elif choice == "3":
                    results[dev] = verify_routes(dev)
                elif choice == "4":
                    results[dev] = verify_vrrp(dev)
                elif choice == "5":
                    results[dev] = verify_nat(dev)
                elif choice == "6":
                    results[dev] = verify_connectivity(dev)
            last_results.update(results)

        elif choice == "7":
            devices = select_devices()
            last_results = run_full_validation(devices)
            print_summary(last_results)

        elif choice == "8":
            if last_results:
                print_summary(last_results)
            else:
                warn("No hay resultados previos. Ejecuta primero una verificación.")

        elif choice == "9":
            if last_results:
                save_report(last_results)
            else:
                warn("No hay resultados para guardar. Ejecuta primero una verificación.")

        else:
            warn("Opción inválida. Intenta de nuevo.")

        input(f"\n  {YELLOW}[Presiona Enter para continuar...]{RESET}")
        # Limpiar pantalla (compatible Windows/Linux)
        os.system("cls" if os.name == "nt" else "clear")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Si se pasa argumento 'auto', ejecuta validación completa sin menú
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        results = run_full_validation(BRANCH2_DEVICES)
        print_summary(results)
        save_report(results)
    else:
        main_menu()
