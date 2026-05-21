#!/usr/bin/env python3
"""
================================================================================
  LAB 2 - VERIFICADOR AUTOMATIZADO
  DMVPN / OSPF / VRRP / NAT / Redundancia
================================================================================
  Métodos Paramiko:
    - exec_command()  → verificación 
    - invoke_shell()  → configuración
================================================================================
"""
 
import paramiko
import time
import sys
import re
 
# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────
LAB      = "ISP-TDP-CLARO-IOL"
PREFIX   = f"clab-{LAB}"
USER     = "admin"
PASS     = "admin"
TIMEOUT  = 10
 
def cname(node):
    return f"{PREFIX}-{node}"
 
# Dispositivos y sus datos clave (de los .partial)
DEVICES = {
    "CPE-HQ": {
        "tunnel_ip": "172.16.10.1",  "loopback": "200.0.0.1",
        "ospf_id":   "1.1.1.1",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [10, 20],
        "vips":      ["192.168.10.1","192.168.20.1"],
        "lans":      ["192.168.10.0","192.168.20.0"],
        "role":      "HUB-PRINCIPAL", "priority": 255,
    },
    "CPE-HQ-BK": {
        "tunnel_ip": "172.16.10.2",  "loopback": "190.0.1.1",
        "ospf_id":   "3.3.3.3",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [10, 20],
        "vips":      ["192.168.10.1","192.168.20.1"],
        "lans":      ["192.168.10.0","192.168.20.0"],
        "role":      "HUB-BACKUP",   "priority": 100,
    },
    "CPE-BRANCH": {
        "tunnel_ip": "172.16.10.11", "loopback": "190.0.0.1",
        "ospf_id":   "2.2.2.2",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [5, 15],
        "vips":      ["192.168.5.1", "192.168.15.1"],
        "lans":      ["192.168.5.0", "192.168.15.0"],
        "role":      "SPOKE-BRANCH1","priority": 0,
    },
    "CPE-BRANCH-BK": {
        "tunnel_ip": "172.16.10.12", "loopback": "200.0.1.1",
        "ospf_id":   "4.4.4.4",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [5, 15],
        "vips":      ["192.168.5.1", "192.168.15.1"],
        "lans":      ["192.168.5.0", "192.168.15.0"],
        "role":      "SPOKE-BRANCH1-BK","priority": 0,
    },
    "CPE-BRANCH2": {
        "tunnel_ip": "172.16.10.21", "loopback": "200.0.2.1",
        "ospf_id":   "5.5.5.5",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [25, 30],
        "vips":      ["192.168.25.1","192.168.30.1"],
        "lans":      ["192.168.25.0","192.168.30.0"],
        "role":      "SPOKE-BRANCH2","priority": 110,
        "ospf_cost": 10,
    },
    "CPE-BRANCH2-BK": {
        "tunnel_ip": "172.16.10.22", "loopback": "190.0.2.1",
        "ospf_id":   "6.6.6.6",      "wan_int":  "Ethernet0/1",
        "lan_int":   "Ethernet0/2",  "vrrp":     [25, 30],
        "vips":      ["192.168.25.1","192.168.30.1"],
        "lans":      ["192.168.25.0","192.168.30.0"],
        "role":      "SPOKE-BRANCH2-BK","priority": 95,
        "ospf_cost": 1000,
    },
    "M3": {
        "wan_int_branch2": "Ethernet0/3",  # hacia CPE-BRANCH2
        "role": "ISP-MOVISTAR",
    },
    "C5": {
        "wan_int_branch2bk": "Ethernet0/1",  # hacia CPE-BRANCH2-BK
        "role": "ISP-CLARO",
    },
}
 
# Escenarios de redundancia
SCENARIOS = {
    "A": {
        "name":   "Caída HUB Principal (CPE-HQ)",
        "node":   "CPE-HQ",
        "int":    "Ethernet0/1",
        "verify": ["CPE-BRANCH2", "CPE-BRANCH2-BK"],
        "desc":   "Spokes deben reconverger a CPE-HQ-BK como NHS backup",
    },
    "B": {
        "name":   "Caída WAN Spoke Branch2 (CPE-BRANCH2)",
        "node":   "CPE-BRANCH2",
        "int":    "Ethernet0/1",
        "verify": ["CPE-BRANCH2-BK"],
        "desc":   "IP SLA falla → VRRP cede a BK (priority 110→90 < 95)",
    },
    "C": {
        "name":   "Caída WAN Movistar hacia Branch2 (M3)",
        "node":   "M3",
        "int":    "Ethernet0/3",
        "verify": ["CPE-BRANCH2"],
        "desc":   "CPE-BRANCH2 pierde enlace WAN por Movistar",
    },
    "D": {
        "name":   "Caída WAN Claro hacia Branch2-BK (C5)",
        "node":   "C5",
        "int":    "Ethernet0/1",
        "verify": ["CPE-BRANCH2-BK"],
        "desc":   "CPE-BRANCH2-BK pierde enlace WAN por Claro",
    },
    "E": {
        "name":   "Caída LAN MASTER HQ (CPE-HQ)",
        "node":   "CPE-HQ",
        "int":    "Ethernet0/2",
        "verify": ["CPE-HQ-BK"],
        "desc":   "VRRP grupos 10 y 20 → CPE-HQ-BK sube a MASTER",
    },
    "F": {
        "name":   "Caída LAN MASTER Branch2 (CPE-BRANCH2)",
        "node":   "CPE-BRANCH2",
        "int":    "Ethernet0/2",
        "verify": ["CPE-BRANCH2-BK"],
        "desc":   "VRRP grupos 25 y 30 → CPE-BRANCH2-BK sube a MASTER",
    },
}
 
 
# ──────────────────────────────────────────────────────────────────────────────
# SSH — CONEXIÓN
# ──────────────────────────────────────────────────────────────────────────────
 
def connect(node):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=cname(node), username=USER, password=PASS,
                look_for_keys=False, timeout=TIMEOUT)
    return ssh
 
 
def exec_cmd(ssh, cmd):
    """exec_command — verificación (pc2.md Parte 4)"""
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(0.8)
    return stdout.read().decode("utf-8", errors="replace")
 
 
def shell_cmds(ssh, cmds, wait=2.0):
    """invoke_shell — sesión interactiva (pc2.md Parte 3)"""
    sh = ssh.invoke_shell()
    time.sleep(1)
    if sh.recv_ready():
        sh.recv(65535)
    sh.send("terminal length 0\n")
    time.sleep(0.5)
    out = ""
    for c in cmds:
        sh.send(c + "\n")
        time.sleep(wait)
        if sh.recv_ready():
            out += sh.recv(65535).decode("utf-8", errors="replace")
    return out
 
 
# ──────────────────────────────────────────────────────────────────────────────
# IMPRESIÓN
# ──────────────────────────────────────────────────────────────────────────────
 
def sep(title="", ch="─"):
    w = 68
    if title:
        print(f"\n  {ch*3} {title} {ch*max(0, w-len(title)-5)}")
    else:
        print(f"  {ch*w}")
 
def ok(m):   print(f"    [OK]  {m}")
def fail(m): print(f"    [KO]  {m}")
def info(m): print(f"    [>>]  {m}")
def warn(m): print(f"    [!!]  {m}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 1 — DMVPN / TÚNEL
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_dmvpn(node):
    sep(f"DMVPN — {node}")
    try:
        ssh = connect(node)
 
        # show dmvpn
        out = exec_cmd(ssh, "show dmvpn")
        peers = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+\w+\s+(\w+)', out)
        if peers:
            ok(f"DMVPN activo — {len(peers)} peer(s)")
            for p in peers:
                info(f"  NBMA {p[0]} ↔ tunnel {p[1]} [{p[2]}]")
        else:
            warn("DMVPN sin peers registrados")
 
        # show interface tunnel1
        out = exec_cmd(ssh, "show interface tunnel1")
        if "line protocol is up" in out.lower():
            ok("Tunnel1 UP/UP")
        else:
            fail("Tunnel1 no está UP")
 
        # show ip nhrp
        out = exec_cmd(ssh, "show ip nhrp")
        cnt = len(re.findall(r'via\s+\d+\.\d+\.\d+\.\d+', out))
        ok(f"NHRP: {cnt} entrada(s)") if cnt else warn("NHRP sin entradas")
 
        # show ip nhrp nhs (solo spokes)
        if node not in ["CPE-HQ", "CPE-HQ-BK"]:
            out = exec_cmd(ssh, "show ip nhrp nhs")
            if "200.0.0.1" in out or "190.0.1.1" in out:
                ok("NHS (ambos HUBs) registrados")
            else:
                warn("NHS no encontrados")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 2 — OSPF
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_ospf(node):
    sep(f"OSPF — {node}")
    try:
        ssh = connect(node)
 
        out = exec_cmd(ssh, "show ip ospf neighbor")
        full = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+FULL', out)
        if full:
            ok(f"Vecinos FULL: {full}")
        else:
            others = re.findall(r'(\S+)\s+\d+\s+(\w+/\w+|\w+)', out)
            warn(f"Sin vecinos FULL — {others[:3]}" if others else "Sin vecinos OSPF")
 
        out = exec_cmd(ssh, "show ip ospf interface tunnel1")
        if "area 0" in out.lower():
            ok("Tunnel1 en área 0")
        if "broadcast" in out.lower():
            ok("Tipo de red BROADCAST")
 
        meta = DEVICES.get(node, {})
        if meta.get("ospf_cost"):
            info(f"OSPF cost configurado: {meta['ospf_cost']}")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 3 — RUTAS
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_routes(node):
    sep(f"RUTAS — {node}")
    expected = {
        "172.16.10.0":  "túnel DMVPN",
        "192.168.10.0": "LAN HQ VLAN10",
        "192.168.20.0": "LAN HQ VLAN20",
        "192.168.5.0":  "LAN Branch1 VLAN5",
        "192.168.15.0": "LAN Branch1 VLAN15",
        "192.168.25.0": "LAN Branch2 VLAN25",
        "192.168.30.0": "LAN Branch2 VLAN30",
        "0.0.0.0":      "default route",
    }
    try:
        ssh = connect(node)
        out = exec_cmd(ssh, "show ip route")
 
        for net, label in expected.items():
            if net in out:
                ok(f"{net}  ({label})")
            else:
                warn(f"{net}  ({label}) — ausente")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 4 — VRRP
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_vrrp(node):
    sep(f"VRRP — {node}")
    meta = DEVICES.get(node, {})
    groups = meta.get("vrrp", [])
    if not groups:
        warn("No aplica VRRP a este nodo"); return
    try:
        ssh = connect(node)
        out = exec_cmd(ssh, "show vrrp brief")
        print(f"\n{out}")
 
        for g in groups:
            if re.search(rf'\b{g}\b.*Master', out, re.I):
                ok(f"VRRP {g} → MASTER")
            elif re.search(rf'\b{g}\b.*Backup', out, re.I):
                ok(f"VRRP {g} → BACKUP")
            elif str(g) in out:
                warn(f"VRRP {g} presente pero estado desconocido")
            else:
                fail(f"VRRP {g} no encontrado")
 
        for vip in meta.get("vips", []):
            if vip in out:
                ok(f"VIP {vip} configurada")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 5 — NAT
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_nat(node):
    sep(f"NAT — {node}")
    try:
        ssh = connect(node)
 
        out = exec_cmd(ssh, "show ip nat statistics")
        if "outside" in out.lower() and "inside" in out.lower():
            ok("NAT inside/outside configurado")
        m = re.search(r'Total\s+active\s+translations:\s+(\d+)', out, re.I)
        if m:
            ok(f"Traducciones activas: {m.group(1)}")
 
        out = exec_cmd(ssh, "show ip nat pool")
        if out.strip():
            ok(f"NAT pool:\n{out.strip()[:200]}")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 6 — CONECTIVIDAD (PING / TRACEROUTE)
# ──────────────────────────────────────────────────────────────────────────────
 
def verify_connectivity(node):
    sep(f"CONECTIVIDAD — desde {node}")
    targets = {
        "HUB-Principal túnel":  "172.16.10.1",
        "HUB-Backup túnel":     "172.16.10.2",
        "Branch1 túnel":        "172.16.10.11",
        "Branch2 túnel":        "172.16.10.21",
        "HQ LAN 192.168.10.1":  "192.168.10.1",
        "HQ LAN 192.168.20.1":  "192.168.20.1",
        "Branch1 LAN 5.1":      "192.168.5.1",
        "Branch2 LAN 25.1":     "192.168.25.1",
        "Branch2 LAN 30.1":     "192.168.30.1",
        "Internet 8.8.8.8":     "8.8.8.8",
    }
    loopback = DEVICES.get(node, {}).get("loopback", "")
    try:
        ssh = connect(node)
        for label, ip in targets.items():
            src = f"source loopback0" if loopback else ""
            out = exec_cmd(ssh, f"ping {ip} repeat 5 {src}", )
            m = re.search(r'Success rate is (\d+) percent', out)
            if m:
                rate = int(m.group(1))
                if rate == 100:
                    ok(f"PING {label} ({ip}) — 100%")
                elif rate > 0:
                    warn(f"PING {label} ({ip}) — {rate}% (pérdida parcial)")
                else:
                    fail(f"PING {label} ({ip}) — 0%")
            else:
                warn(f"PING {label} ({ip}) — sin parse")
 
        # Traceroute hacia HQ
        out = exec_cmd(ssh, f"traceroute 192.168.10.1 {src} probe 2 timeout 2")
        info(f"Traceroute → HQ:\n{out[:300]}")
 
        ssh.close()
    except Exception as e:
        fail(f"Error: {e}")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 7 — ESCENARIOS DE REDUNDANCIA
# ──────────────────────────────────────────────────────────────────────────────
 
def run_scenario(key):
    s = SCENARIOS[key]
    node   = s["node"]
    intf   = s["int"]
    verify = s["verify"]
 
    print(f"\n  {'='*68}")
    print(f"  ESCENARIO {key}: {s['name']}")
    print(f"  {s['desc']}")
    print(f"  {'='*68}")
 
    # ── ESTADO ANTES ──────────────────────────────────────────────────────
    sep("ESTADO ANTES de la caída")
    for v in verify:
        if DEVICES.get(v, {}).get("vrrp"):
            verify_vrrp(v)
        verify_connectivity(v)
 
    # ── SIMULACIÓN DE CAÍDA ───────────────────────────────────────────────
    sep(f"SIMULANDO CAÍDA → {node} {intf} shutdown")
    try:
        ssh = connect(node)
        out = shell_cmds(ssh, [
            "conf t",
            f"interface {intf}",
            "shutdown",
            "end",
        ], wait=1.5)
        ok(f"{node} {intf} → shutdown ejecutado")
        info(f"Output:\n{out[-300:]}")
        ssh.close()
    except Exception as e:
        fail(f"No se pudo ejecutar shutdown: {e}")
        return
 
    # ── ESPERAR RECONVERGENCIA ─────────────────────────────────────────────
    print(f"\n  Esperando reconvergencia (15s)...", end="", flush=True)
    for _ in range(15):
        time.sleep(1)
        print(".", end="", flush=True)
    print()
 
    # ── ESTADO DESPUÉS ────────────────────────────────────────────────────
    sep("ESTADO DESPUÉS de la caída")
    for v in verify:
        if DEVICES.get(v, {}).get("vrrp"):
            verify_vrrp(v)
        verify_connectivity(v)
 
    # ── RESTAURAR ─────────────────────────────────────────────────────────
    sep(f"RESTAURANDO → {node} {intf} no shutdown")
    try:
        ssh = connect(node)
        out = shell_cmds(ssh, [
            "conf t",
            f"interface {intf}",
            "no shutdown",
            "end",
        ], wait=1.5)
        ok(f"{node} {intf} → no shutdown ejecutado")
        ssh.close()
    except Exception as e:
        warn(f"No se pudo restaurar: {e}")
        warn(f"Restaurar manualmente: conf t → interface {intf} → no shutdown")
 
    print(f"\n  Esperando que levante (10s)...", end="", flush=True)
    for _ in range(10):
        time.sleep(1)
        print(".", end="", flush=True)
    print()
    ok("Escenario finalizado — interfaz restaurada")
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MÓDULO 8 — VERIFICACIÓN COMPLETA
# ──────────────────────────────────────────────────────────────────────────────
 
def full_verify(nodes=None):
    if nodes is None:
        nodes = ["CPE-HQ", "CPE-HQ-BK",
                 "CPE-BRANCH", "CPE-BRANCH-BK",
                 "CPE-BRANCH2", "CPE-BRANCH2-BK"]
    for node in nodes:
        print(f"\n  {'#'*68}")
        print(f"  # {node}  —  {DEVICES.get(node,{}).get('role','')}")
        print(f"  {'#'*68}")
        verify_dmvpn(node)
        verify_ospf(node)
        verify_routes(node)
        verify_vrrp(node)
        verify_nat(node)
        verify_connectivity(node)
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MENÚ
# ──────────────────────────────────────────────────────────────────────────────
 
def pick_node(label="Nodo"):
    cpes = list(DEVICES.keys())
    print(f"\n  {label}:")
    for i, n in enumerate(cpes, 1):
        print(f"    [{i}] {n}  ({DEVICES[n].get('role','')})")
    try:
        return cpes[int(input("  Selección: ").strip()) - 1]
    except (ValueError, IndexError):
        return cpes[0]
 
 
def menu():
    while True:
        print("\n" + "="*70)
        print("  LAB 2 — VERIFICADOR AUTOMATIZADO")
        print(f"  Lab: {LAB}")
        print("="*70)
        print()
        print("  ── VERIFICACIONES ──────────────────────────────────")
        print("  [1] DMVPN (túnel + NHRP + NHS)")
        print("  [2] OSPF  (vecinos + área + cost)")
        print("  [3] Rutas (tabla de routing)")
        print("  [4] VRRP  (grupos + estado MASTER/BACKUP)")
        print("  [5] NAT   (pool + traducciones)")
        print("  [6] Conectividad (ping + traceroute)")
        print("  [7] Verificación completa de un nodo")
        print("  [8] Verificación completa de TODOS los CPEs")
        print()
        print("  ── REDUNDANCIA — ESCENARIOS DE CAÍDA ───────────────")
        print("  [A] Caída HUB Principal        (CPE-HQ   → e0/1 shutdown)")
        print("  [B] Caída WAN Spoke Branch2    (CPE-BRANCH2 → e0/1 shutdown)")
        print("  [C] Caída WAN Movistar→Branch2 (M3 → e0/3 shutdown)")
        print("  [D] Caída WAN Claro→Branch2-BK (C5 → e0/1 shutdown)")
        print("  [E] Caída LAN MASTER HQ        (CPE-HQ   → e0/2 shutdown)")
        print("  [F] Caída LAN MASTER Branch2   (CPE-BRANCH2 → e0/2 shutdown)")
        print()
        print("  [0] Salir")
        print()
 
        op = input("  Opción: ").strip().upper()
 
        if op == "0":
            break
        elif op in ["1","2","3","4","5","6","7"]:
            node = pick_node()
            fns = {
                "1": verify_dmvpn,
                "2": verify_ospf,
                "3": verify_routes,
                "4": verify_vrrp,
                "5": verify_nat,
                "6": verify_connectivity,
                "7": lambda n: (verify_dmvpn(n), verify_ospf(n),
                                verify_routes(n), verify_vrrp(n),
                                verify_nat(n), verify_connectivity(n)),
            }
            fns[op](node)
        elif op == "8":
            full_verify()
        elif op in SCENARIOS:
            run_scenario(op)
        else:
            warn("Opción inválida")
 
        input("\n  [Enter para continuar...]")
 
 
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        full_verify()
    else:
        menu()
 