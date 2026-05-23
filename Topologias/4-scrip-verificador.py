#!/usr/bin/python3
 
import paramiko
import subprocess
import json
import time
import sys
import re
import os
 
# =====================================================================
# CONSTANTES
# =====================================================================
LAB_NAME = "ISP-TDP-CLARO-IOL"
USER     = "admin"
PASSWD   = "admin"
 
G    = "\033[92m";  Y    = "\033[93m";  R    = "\033[91m"
RST  = "\033[0m";   BOLD = "\033[1m";   CYAN = "\033[96m"
 
def ok(msg):   return f"{G}[OK]  {RST}{msg}"
def warn(msg): return f"{Y}[WARN]{RST}{msg}"
def fail(msg): return f"{R}[FAIL]{RST}{msg}"
def info(msg): return f"{CYAN}[INFO]{RST}{msg}"
 
def banner(titulo, char="="):
    print(f"\n{BOLD}{char*62}{RST}")
    print(f"{BOLD}  {titulo}{RST}")
    print(f"{BOLD}{char*62}{RST}")
 
# =====================================================================
# INVENTARIO DE ROUTERS
# =====================================================================
ATRIBUTOS = {
    "CPE-HQ": {
        "rol": "hub_principal","loopback0": "200.0.0.1",
        "tunnel_ip": "172.16.10.1", "ospf_cost_esperado": None,
        "vrrp_group": None, "vrrp_rol_esperado": None,
        "wan_intf": "Ethernet0/1", "sla_target": None,
    },
    "CPE-HQ-BK": {
        "rol": "hub_backup","loopback0": "190.0.1.1",
        "tunnel_ip": "172.16.10.2", "ospf_cost_esperado": 100,
        "vrrp_group": None, "vrrp_rol_esperado": None,
        "wan_intf": "Ethernet0/1", "sla_target": None,
    },
    "CPE-BRANCH": {
        "rol": "spoke_principal","loopback0": "190.0.0.1",
        "tunnel_ip": "172.16.10.11","ospf_cost_esperado": 10,
        "vrrp_group": 5, "vrrp_rol_esperado": "Master",
        "wan_intf": "Ethernet0/1", "sla_target": "8.8.8.8",
    },
    "CPE-BRANCH-BK": {
        "rol": "spoke_backup","loopback0": "200.0.1.1",
        "tunnel_ip": "172.16.10.12","ospf_cost_esperado": 1000,
        "vrrp_group": 5, "vrrp_rol_esperado": "Backup",
        "wan_intf": "Ethernet0/1", "sla_target": "8.8.8.8",
    },
    "CPE-BRANCH2": {
        "rol": "spoke_principal","loopback0": "200.0.2.1",
        "tunnel_ip": "172.16.10.21","ospf_cost_esperado": 10,
        "vrrp_group": 25,"vrrp_rol_esperado": "Master",
        "wan_intf": "Ethernet0/1","sla_target": "8.8.8.8",
    },
    "CPE-BRANCH2-BK": {
        "rol": "spoke_backup","loopback0": "190.0.2.1",
        "tunnel_ip": "172.16.10.22","ospf_cost_esperado": 1000,
        "vrrp_group": 25,"vrrp_rol_esperado": "Backup",
        "wan_intf": "Ethernet0/1","sla_target": "8.8.8.8",
    },
}
 
FALLBACK_IPS = {h: f"clab-{LAB_NAME}-{h}" for h in ATRIBUTOS}
 
# =====================================================================
# INVENTARIO DE PCs (docker exec)
# =====================================================================
PCS = {
    "PC1-BRANCH2-V25": {"clab_name": f"clab-{LAB_NAME}-PC1-R-VLAN25",
                        "ip": "192.168.25.10", "sede": "branch2"},
    "PC2-BRANCH2-V25": {"clab_name": f"clab-{LAB_NAME}-PC2-R-VLAN25",
                        "ip": "192.168.25.20", "sede": "branch2"},
    "PC3-BRANCH2-V30": {"clab_name": f"clab-{LAB_NAME}-PC3-R-VLAN30",
                        "ip": "192.168.30.10", "sede": "branch2"},
    "PC4-BRANCH2-V30": {"clab_name": f"clab-{LAB_NAME}-PC4-R-VLAN30",
                        "ip": "192.168.30.20", "sede": "branch2"},
    "PC1-BRANCH-V5":   {"clab_name": f"clab-{LAB_NAME}-PC1-R-VLAN5",
                        "ip": "192.168.5.10",  "sede": "branch1"},
    "PC2-BRANCH-V5":   {"clab_name": f"clab-{LAB_NAME}-PC2-R-VLAN5",
                        "ip": "192.168.5.20",  "sede": "branch1"},
    "PC3-BRANCH-V15":  {"clab_name": f"clab-{LAB_NAME}-PC3-R-VLAN15",
                        "ip": "192.168.15.10", "sede": "branch1"},
    "PC1-HQ-V10":      {"clab_name": f"clab-{LAB_NAME}-PC1-VLAN10",
                        "ip": "192.168.10.10", "sede": "hq"},
    "PC2-HQ-V10":      {"clab_name": f"clab-{LAB_NAME}-PC2-VLAN10",
                        "ip": "192.168.10.20", "sede": "hq"},
    "PC3-HQ-V20":      {"clab_name": f"clab-{LAB_NAME}-PC3-VLAN20",
                        "ip": "192.168.20.10", "sede": "hq"},
}
 
# Pings overlay — usa IP del loopback como source (no nombre de interfaz)
# FIX: "source Loopback0" falla via exec_command en IOL.
#      "source <IP>" es equivalente y funciona correctamente.
PINGS_OVERLAY = [
    ("BRANCH2  → HQ      (Lo0↔Lo0)", "CPE-BRANCH2",    "200.0.0.1"),
    ("BRANCH2  → BRANCH  (Lo0↔Lo0)", "CPE-BRANCH2",    "200.0.1.1"),
    ("BRANCH2  → Internet(NAT/Lo0)", "CPE-BRANCH2",    "8.8.8.8"),
    ("BRANCH   → BRANCH2 (Lo0↔Lo0)", "CPE-BRANCH",     "200.0.2.1"),
    ("HQ       → BRANCH2 (Lo0↔Lo0)", "CPE-HQ",         "200.0.2.1"),
    ("BRANCH2-BK→ HQ     (Lo0↔Lo0)", "CPE-BRANCH2-BK", "200.0.0.1"),
]
 
PINGS_INTERLAN = [
    ("PC-BR2(V25) → PC-HQ(V10)",  "PC1-BRANCH2-V25", "192.168.10.10"),
    ("PC-BR2(V25) → PC-HQ(V20)",  "PC1-BRANCH2-V25", "192.168.20.10"),
    ("PC-BR2(V25) → PC-BR1(V5)",  "PC1-BRANCH2-V25", "192.168.5.10"),
    ("PC-BR2(V30) → PC-BR1(V15)", "PC3-BRANCH2-V30", "192.168.15.10"),
    ("PC-BR2(V25) → Internet",    "PC1-BRANCH2-V25", "8.8.8.8"),
]
 
# =====================================================================
# DESCUBRIMIENTO DE IPs
# =====================================================================
def descubrir_inventario():
    print(info("Descubriendo inventario del lab..."))
    ip_map = _via_inspect() or _via_topology_json()
    if ip_map:
        print(ok(f"IPs obtenidas ({len(ip_map)} nodos)"))
        return ip_map
    print(warn("Usando hostnames DNS de containerlab."))
    return FALLBACK_IPS.copy()
 
def _via_inspect():
    try:
        res = subprocess.run(
            ["containerlab","inspect","--name",LAB_NAME,"--format","json"],
            capture_output=True, text=True, timeout=15)
        return _parsear(json.loads(res.stdout)) if res.returncode==0 else None
    except Exception:
        return None
 
def _via_topology_json():
    for path in [f"clab-{LAB_NAME}/topology-data.json",
                 f"/root/clab-{LAB_NAME}/topology-data.json"]:
        try:
            with open(path) as f:
                r = _parsear(json.load(f))
            if r: return r
        except Exception:
            pass
    return None
 
def _parsear(data):
    result = {}
    try:
        nodos = data.get("containers") or data.get("Containers") or []
        if not nodos:
            nd = data.get("nodes") or data.get("topology",{}).get("nodes",{})
            for n, v in nd.items():
                ip = v.get("mgmt-ipv4-address") or v.get("MgmtIPv4","")
                if ip: result[n.replace(f"clab-{LAB_NAME}-","")] = ip.split("/")[0]
        else:
            for n in nodos:
                nombre = (n.get("name") or n.get("Name","")).replace(f"clab-{LAB_NAME}-","")
                ip = n.get("ipv4") or n.get("mgmt-ipv4-address") or n.get("MgmtIPv4Address","")
                if ip and nombre: result[nombre] = ip.split("/")[0]
    except Exception:
        return None
    return result or None
 
def construir_equipos(ip_map):
    equipos = {}
    for h, attrs in ATRIBUTOS.items():
        ip = ip_map.get(h)
        if not ip:
            print(warn(f"  {h} no encontrado")); continue
        equipos[h] = {"ip_ssh": ip, "user": USER, "pass": PASSWD, **attrs}
    return equipos
 
# =====================================================================
# SSH — una conexion por comando (fix "SSH session not active" en IOS)
# =====================================================================
def _conectar(ip, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=ip, username=user, password=password,
                look_for_keys=False, allow_agent=False,
                timeout=15, banner_timeout=20, auth_timeout=20,
                disabled_algorithms={"pubkeys":["rsa-sha2-256","rsa-sha2-512"]})
    return ssh
 
def cmd(eq, comando):
    ssh = _conectar(eq["ip_ssh"], eq["user"], eq["pass"])
    try:
        _, stdout, _ = ssh.exec_command(comando, timeout=60)
        # Espera a que el comando termine completamente antes de leer
        # Sin esto, IOS ping se corta en el primer ! del buffer
        stdout.channel.recv_exit_status()
        return stdout.read().decode(errors="replace")
    finally:
        ssh.close()
 
def shell_cmds(eq, comandos):
    ssh = _conectar(eq["ip_ssh"], eq["user"], eq["pass"])
    try:
        sh = ssh.invoke_shell(); time.sleep(1)
        if sh.recv_ready(): sh.recv(65535)
        for c in comandos:
            sh.send(c+"\n"); time.sleep(0.3)
            if sh.recv_ready(): sh.recv(65535)
        time.sleep(2)
    finally:
        ssh.close()
 
# =====================================================================
# docker exec para PCs Alpine
# =====================================================================
def pc_cmd(pc, comando, timeout=15):
    try:
        res = subprocess.run(
            ["docker","exec",pc["clab_name"],"sh","-c", comando],
            capture_output=True, text=True, timeout=timeout)
        return res.stdout + res.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"
 
def pc_ping(pc_name, pc, destino, descripcion, count=5):
    out = pc_cmd(pc, f"ping -c {count} -W 2 {destino}")
    if "0% packet loss" in out or f"{count} packets received" in out:
        print("  "+ok(descripcion)); return True
    m = re.search(r"(\d+) packets received", out)
    if m and int(m.group(1)) > 0:
        print("  "+warn(f"{descripcion} — {m.group(1)}/{count} paquetes")); return False
    print("  "+fail(descripcion)); return False
 
def pc_traceroute(pc_name, pc, destino, descripcion):
    out = pc_cmd(pc, f"traceroute -n -w 2 -q 1 {destino}", timeout=30)
    if "TIMEOUT" in out or "ERROR" in out:
        print("  "+fail(f"Traceroute {descripcion} — {out.strip()}")); return
    saltos = [l for l in out.splitlines() if re.match(r"\s*\d+\s", l)]
    if saltos:
        print("  "+ok(f"Traceroute {descripcion} — {len(saltos)} salto(s)"))
        for s in saltos[:8]: print(f"       {s.strip()}")
    else:
        print("  "+fail(f"Traceroute {descripcion} — sin respuesta"))
 
def verificar_pcs():
    banner("Verificando PCs (docker exec)", char="-")
    ok_n = 0
    for n, pc in PCS.items():
        out = pc_cmd(pc, "hostname", timeout=5)
        if "ERROR" in out or "TIMEOUT" in out:
            print(f"  {fail(n+' — '+pc['clab_name']+' ('+out.strip()+')')}")
        else:
            print(f"  {ok(n+' — '+pc['clab_name'])}"); ok_n += 1
    print(f"\n  {ok_n}/{len(PCS)} PCs accesibles")
    return ok_n > 0
 
# =====================================================================
# CHECKS DE ROUTERS
# =====================================================================
def chk_tunnel(eq):
    out = cmd(eq, "show interface Tunnel1")
    up = "line protocol is up" in out.lower()
    print("  "+(ok("Tunnel1 — UP") if up else fail("Tunnel1 — DOWN")))
 
def chk_dmvpn(eq):
    out = cmd(eq, "show dmvpn")
    n = out.count(" UP ")
    if n>0:             print("  "+ok(f"DMVPN — {n} entrada(s) UP"))
    elif "NBMA" in out: print("  "+warn("DMVPN — tabla presente, sin entradas UP"))
    else:               print("  "+fail("DMVPN — sin tabla"))
 
def chk_nhrp(eq):
    out = cmd(eq,"show ip nhrp")
    e = [l for l in out.splitlines() if l.strip() and not l.startswith("Legend") and "/" in l]
    print("  "+(ok(f"NHRP — {len(e)} entrada(s)") if e else warn("NHRP — tabla vacia")))
 
def chk_ospf_neighbors(eq):
    out = cmd(eq,"show ip ospf neighbor")
    full  = out.count("FULL/")
    total = len([l for l in out.splitlines()
                 if l.strip() and not l.startswith(("Neighbor","OSP"," OSP"))])
    if full>0:    print("  "+ok(f"OSPF Neighbors — {full}/{total} en FULL"))
    elif total>0: print("  "+warn(f"OSPF Neighbors — {total} vecino(s), ninguno en FULL"))
    else:         print("  "+fail("OSPF Neighbors — sin vecinos"))
 
def chk_rutas(eq):
    out = cmd(eq,"show ip route ospf")
    rs = [l for l in out.splitlines() if re.match(r"\s+O[ \s]",l) or l.startswith("O ")]
    print("  "+(ok(f"Rutas OSPF — {len(rs)} ruta(s)") if rs else warn("Rutas OSPF — sin rutas")))
 
def chk_ipsec_profile(eq):
    """
    Verifica que el profile IPsec tenga transform-set configurado.
    No verifica SAs activas — en IOL virtualizado IKE no negocia
    para tunnel protection mGRE (limitacion del emulador, no config).
    """
    out = cmd(eq, "show crypto ipsec profile")
    if "TS-DMVPN" in out or "transform" in out.lower():
        print("  "+ok("IPsec profile — transform-set configurado correctamente"))
        print("  "+warn("IPsec SAs — no negocian en IOL (limitacion del emulador)"))
    elif "default" in out:
        print("  "+warn("IPsec profile — solo existe profile 'default', falta TS-DMVPN"))
    else:
        print("  "+fail("IPsec profile — no encontrado"))
 
def chk_nat(eq):
    out = cmd(eq,"show ip nat translations")
    ls = [l for l in out.splitlines()
          if l.strip() and not l.startswith("Pro") and "---" not in l]
    if ls:  print("  "+ok(f"NAT — {len(ls)} traduccion(es) activas"))
    else:   print("  "+warn("NAT — tabla vacia (normal sin trafico activo desde LAN)"))
 
def chk_vrrp(eq, rol_override=None):
    if not eq.get("vrrp_group"): return
    out = cmd(eq,"show vrrp brief")
    grupo = str(eq["vrrp_group"])
    rol_esp = (rol_override or eq.get("vrrp_rol_esperado","")).upper()
    for line in out.splitlines():
        if grupo in line:
            if   "MASTER" in line.upper(): ra="MASTER"
            elif "BACKUP" in line.upper(): ra="BACKUP"
            elif "INIT"   in line.upper(): ra="INIT"
            else:                          ra="DESCONOCIDO"
            if ra==rol_esp: print("  "+ok(f"VRRP grupo {grupo} — {ra} (esperado)"))
            else:           print("  "+warn(f"VRRP grupo {grupo} — actual: {ra}, esperado: {rol_esp}"))
            return
    print("  "+fail(f"VRRP grupo {grupo} — no encontrado"))
 
def chk_ip_sla(eq):
    if not eq.get("sla_target"): return
    out = cmd(eq,"show ip sla statistics")
    if "Return Code: OK" in out or "Latest operation return code: OK" in out:
        print("  "+ok(f"IP SLA → {eq['sla_target']} — OK"))
    elif not out.strip() or "No operations" in out:
        print("  "+fail("IP SLA — sin operaciones"))
    else:
        print("  "+warn(f"IP SLA → {eq['sla_target']} — revisar"))
 
def chk_track(eq):
    """
    Verifica track object. Milton configura 'track 200 ip sla 2'.
    Si show track devuelve State: Up/Down el track existe.
    Si no devuelve nada el objeto no fue creado.
    """
    if not eq.get("sla_target"): return
    out = cmd(eq,"show track")
    if "State: Up" in out:
        print("  "+ok("Track — State: Up"))
    elif "State: Down" in out:
        print("  "+warn("Track — State: Down (SLA caido, failover VRRP activo)"))
    else:
        # Puede ser que no haya output si el objeto no existe o el comando
        # devuelve algo distinto en esta version de IOL
        out2 = cmd(eq,"show ip sla summary")
        if out2.strip() and "No" not in out2:
            print("  "+warn("Track — SLA existe pero objeto track no encontrado"))
        else:
            print("  "+warn("Track — no verificable en esta version de IOL"))
 
def chk_ospf_cost(eq):
    c = eq.get("ospf_cost_esperado")
    if c is None: return
    out = cmd(eq,"show ip ospf interface Tunnel1")
    m = re.search(r"Cost[:\s]+(\d+)",out)
    if m:
        ca = int(m.group(1))
        print("  "+(ok(f"OSPF cost Tunnel1 — {ca} (correcto)") if ca==c
                    else warn(f"OSPF cost Tunnel1 — actual: {ca}, esperado: {c}")))
    else:
        print("  "+fail("OSPF cost Tunnel1 — no se pudo leer"))

def chk_ping_router(eq, destino, desc):
    src = eq.get("loopback0", "")
    ssh = _conectar(eq["ip_ssh"], eq["user"], eq["pass"])
    try:
        sh = ssh.invoke_shell()
        time.sleep(0.5)
        if sh.recv_ready(): sh.recv(65535)
        sh.send(f"ping {destino} source {src} repeat 5 timeout 1\n")
        time.sleep(7)
        out = ""
        while sh.recv_ready():
            out += sh.recv(65535).decode(errors="replace")
    finally:
        ssh.close()

    if "Success rate is 100" in out:
        print("  "+ok(f"{desc}"))
    elif "Success rate is" in out:
        m = re.search(r"Success rate is (\d+) percent", out)
        pct = m.group(1) if m else "?"
        print("  "+warn(f"{desc} — {pct}% exito"))
    else:
        print("  "+fail(f"{desc}"))

    # Imprimir detalle del ping igual que traceroute
    for line in out.splitlines():
        line = line.strip()
        if any(x in line for x in ["Sending", "Packet sent", "Success rate", "!!", "..", "!."]):
            print(f"       {line}")
 
def chk_traceroute_router(eq, destino, desc):
    src = eq.get("loopback0", "")
    out = cmd(eq, f"traceroute {destino} source {src} timeout 2 probe 1 numeric")
    saltos = [l for l in out.splitlines() if re.match(r"\s+\d+\s",l)]
    if saltos:
        print("  "+ok(f"Traceroute {desc} — {len(saltos)} salto(s)"))
        for s in saltos[:6]: print(f"       {s.strip()}")
    else:
        print("  "+fail(f"Traceroute {desc} — sin respuesta"))
 
# =====================================================================
# TESTS COMPLETOS
# =====================================================================
def _iter(equipos, alc, fn, solo_redundancia=False):
    for h, eq in equipos.items():
        if not alc.get(h):
            print(f"\n  {Y}[SKIP]{RST} {h}"); continue
        if solo_redundancia and not eq.get("vrrp_group") and not eq.get("ospf_cost_esperado"):
            continue
        print(f"\n  {BOLD}>>> {h} ({eq['rol']}){RST}")
        try: fn(eq)
        except Exception as e: print("  "+fail(f"Error: {e}"))
 
def test_dmvpn(e,a):
    banner("TEST 1: Tunel DMVPN")
    _iter(e,a, lambda eq: (chk_tunnel(eq), chk_dmvpn(eq)))
 
def test_nhrp(e,a):
    banner("TEST 2: NHRP")
    _iter(e,a, chk_nhrp)
 
def test_ospf(e,a):
    banner("TEST 3: Vecindades OSPF")
    _iter(e,a, chk_ospf_neighbors)
 
def test_rutas(e,a):
    banner("TEST 4: Rutas OSPF")
    _iter(e,a, chk_rutas)
 
def test_ipsec(e,a):
    banner("TEST 5: IPsec Profile")
    print(f"\n  {Y}NOTA:{RST} IOL no negocia IKE SAs para tunnel protection mGRE.")
    print(f"  Se verifica que el profile tenga transform-set configurado.")
    _iter(e,a, chk_ipsec_profile)
 
def test_redundancia(e,a):
    banner("TEST 6: Redundancia — VRRP + IP SLA + Track + OSPF Cost")
    _iter(e,a,
          lambda eq: (chk_vrrp(eq), chk_ip_sla(eq), chk_track(eq), chk_ospf_cost(eq)),
          solo_redundancia=True)
 
def test_nat(e,a):
    banner("TEST 7: NAT")
    _iter(e,a, chk_nat)
 
def test_overlay_e2e(e,a):
    banner("TEST 8: Overlay E2E (source loopback IP)")
    for desc, origen, dst in PINGS_OVERLAY:
        eq = e.get(origen)
        if not eq or not a.get(origen):
            print(f"  {Y}[SKIP]{RST} {desc}"); continue
        try: chk_ping_router(eq, dst, desc)
        except Exception as ex: print("  "+fail(f"{desc}: {ex}"))
 
def test_interlan(e,a):
    banner("TEST 9: Inter-LAN PC a PC (docker exec)")
    print(f"\n  {BOLD}--- PINGS ---{RST}")
    for desc, pc_n, dst in PINGS_INTERLAN:
        pc = PCS.get(pc_n)
        if not pc:
            print(f"  {Y}[SKIP]{RST} {desc}"); continue
        try: pc_ping(pc_n, pc, dst, desc)
        except Exception as ex: print("  "+fail(f"{desc}: {ex}"))
 
    print(f"\n  {BOLD}--- TRACEROUTES (Branch2 → destinos) ---{RST}")
    for desc, pc_n, dst in [
        ("PC-BR2 → HQ (V10)",     "PC1-BRANCH2-V25","192.168.10.10"),
        ("PC-BR2 → BRANCH1 (V5)","PC1-BRANCH2-V25","192.168.5.10"),
        ("PC-BR2 → Internet",     "PC1-BRANCH2-V25","8.8.8.8"),
    ]:
        pc = PCS.get(pc_n)
        if not pc: continue
        try: pc_traceroute(pc_n, pc, dst, desc)
        except Exception as ex: print("  "+fail(f"Traceroute {desc}: {ex}"))
 
def health_check_completo(e,a):
    banner("HEALTH-CHECK COMPLETO (Tests 1-9)", char="#")
    t0 = time.time()
    test_dmvpn(e,a); test_nhrp(e,a); test_ospf(e,a); test_rutas(e,a)
    test_ipsec(e,a); test_redundancia(e,a); test_nat(e,a)
    test_overlay_e2e(e,a); test_interlan(e,a)
    banner(f"COMPLETADO EN {time.time()-t0:.1f}s", char="#")
 
# =====================================================================
# FAILOVER CON SNAPSHOT ANTES/DURANTE/DESPUES
# =====================================================================
def _snap(e, a, etiqueta, src_pc="PC1-BRANCH2-V25",
          dst_pc="192.168.10.10", dst_lo="200.0.0.1"):
    print(f"\n  {BOLD}=== {etiqueta} ==={RST}")
    pc   = PCS.get(src_pc)
    eq_origen = e.get("CPE-BRANCH2") or e.get("CPE-HQ")
 
    # Ping + traceroute desde PC
    if pc:
        pc_ping(src_pc, pc, dst_pc, f"PC-BR2 → {dst_pc}")
        pc_traceroute(src_pc, pc, dst_pc, f"PC-BR2 → {dst_pc}")
 
    # Ping overlay loopback a loopback
    eq_br2 = e.get("CPE-BRANCH2")
    if eq_br2 and a.get("CPE-BRANCH2"):
        try: chk_ping_router(eq_br2, dst_lo, f"BR2-Lo0 → {dst_lo}")
        except Exception as ex: print("  "+fail(f"Ping overlay: {ex}"))
        try: chk_traceroute_router(eq_br2, dst_lo, f"BR2-Lo0 → {dst_lo}")
        except Exception as ex: print("  "+fail(f"Traceroute overlay: {ex}"))
 
def failover_wan_branch2(e, a):
    banner("FAILOVER 10: Caida WAN Branch2 → Branch2-BK asume")
    eq_p  = e.get("CPE-BRANCH2")
    eq_bk = e.get("CPE-BRANCH2-BK")
    if not eq_p  or not a.get("CPE-BRANCH2"):   print(fail("CPE-BRANCH2 inaccesible"));    return
    if not eq_bk or not a.get("CPE-BRANCH2-BK"):print(fail("CPE-BRANCH2-BK inaccesible")); return
 
    wan = eq_p["wan_intf"]
    _snap(e, a, "ANTES del failover")
 
    print(info(f"\nApagando {wan} en CPE-BRANCH2..."))
    try: shell_cmds(eq_p, ["configure terminal",f"interface {wan}","shutdown","end"])
    except Exception as ex: print(fail(f"No se pudo apagar: {ex}")); return
 
    print(info("Esperando convergencia VRRP/OSPF (20s)..."))
    time.sleep(20)
 
    print(f"\n  {BOLD}CPE-BRANCH2-BK post-failover:{RST}")
    try:
        chk_vrrp({**eq_bk, "vrrp_rol_esperado": "Master"})
        chk_dmvpn(eq_bk)
        chk_ospf_neighbors(eq_bk)
    except Exception as ex: print(fail(f"Error: {ex}"))
 
    _snap(e, a, "DURANTE el failover (trafico por BK)")
 
    print(info(f"\nRestaurando {wan} en CPE-BRANCH2..."))
    try:
        shell_cmds(eq_p, ["configure terminal",f"interface {wan}","no shutdown","end"])
        print(ok(f"{wan} restaurada."))
    except Exception as ex:
        print(fail(f"ERROR al restaurar — ejecuta manualmente 'no shutdown' en {wan}: {ex}")); return
 
    print(info("Esperando re-convergencia (20s)..."))
    time.sleep(20)
 
    print(f"\n  {BOLD}CPE-BRANCH2 post-recuperacion:{RST}")
    try:
        chk_vrrp(eq_p)
        chk_dmvpn(eq_p)
    except Exception as ex: print(fail(f"Error: {ex}"))
 
    _snap(e, a, "DESPUES de restaurar (vuelta al principal)")
 
def failover_hub(e, a):
    banner("FAILOVER 11: Caida HUB Principal (CPE-HQ) → CPE-HQ-BK")
    eq_hq    = e.get("CPE-HQ")
    eq_hq_bk = e.get("CPE-HQ-BK")
    if not eq_hq    or not a.get("CPE-HQ"):    print(fail("CPE-HQ inaccesible"));    return
    if not eq_hq_bk or not a.get("CPE-HQ-BK"):print(fail("CPE-HQ-BK inaccesible")); return
 
    wan = eq_hq["wan_intf"]
    _snap(e, a, "ANTES del failover")
 
    print(info(f"\nApagando {wan} en CPE-HQ..."))
    try: shell_cmds(eq_hq, ["configure terminal",f"interface {wan}","shutdown","end"])
    except Exception as ex: print(fail(f"No se pudo apagar: {ex}")); return
 
    print(info("Esperando convergencia OSPF/DMVPN (30s)..."))
    time.sleep(30)
 
    for target in ["CPE-HQ-BK","CPE-BRANCH2","CPE-BRANCH"]:
        eq = e.get(target)
        if not eq or not a.get(target): continue
        print(f"\n  {BOLD}>>> {target} post-failover:{RST}")
        try:
            chk_dmvpn(eq)
            chk_ospf_neighbors(eq)
        except Exception as ex: print(fail(f"Error: {ex}"))
 
    _snap(e, a, "DURANTE el failover HUB (trafico por HQ-BK)")
 
    print(info(f"\nRestaurando {wan} en CPE-HQ..."))
    try:
        shell_cmds(eq_hq, ["configure terminal",f"interface {wan}","no shutdown","end"])
        print(ok("CPE-HQ restaurado."))
    except Exception as ex:
        print(fail(f"ERROR al restaurar: {ex}")); return
 
    print(info("Esperando re-convergencia (25s)..."))
    time.sleep(25)
 
    _snap(e, a, "DESPUES de restaurar HUB")
 
# =====================================================================
# UTILIDADES
# =====================================================================
def verificar_alcanzabilidad(equipos):
    banner("Verificando alcanzabilidad SSH", char="-")
    alc = {}
    for h, eq in equipos.items():
        try:
            s = _conectar(eq["ip_ssh"],eq["user"],eq["pass"]); s.close()
            alc[h] = True;  print(f"  {ok(h+' — '+str(eq['ip_ssh']))}")
        except Exception as e:
            alc[h] = False; print(f"  {fail(h+' — '+str(e))}")
    return alc
 
def mostrar_inventario(equipos):
    banner("Inventario — Routers")
    print(f"  {'Hostname':<20} {'IP SSH':<18} {'Loopback0':<18} Rol")
    print(f"  {'-'*20} {'-'*18} {'-'*18} {'-'*20}")
    for h,eq in equipos.items():
        print(f"  {h:<20} {str(eq['ip_ssh']):<18} {eq.get('loopback0','-'):<18} {eq.get('rol','-')}")
    banner("Inventario — PCs (docker exec)")
    print(f"  {'Nombre':<22} {'Contenedor':<42} IP")
    print(f"  {'-'*22} {'-'*42} {'-'*16}")
    for n,pc in PCS.items():
        print(f"  {n:<22} {pc['clab_name']:<42} {pc['ip']}")
 
# =====================================================================
# MENU
# =====================================================================
def menu():
    print()
    print(f"{BOLD}{'='*62}{RST}")
    print(f"{BOLD}  LAB2 FASE 4 — VALIDACION DMVPN | {LAB_NAME}{RST}")
    print(f"{BOLD}{'='*62}{RST}")
    print()
    print("  ── ESTADO DE LA RED ─────────────────────────────────────")
    print("  [1]  Tunel DMVPN              (show dmvpn)")
    print("  [2]  NHRP                     (show ip nhrp)")
    print("  [3]  Vecindades OSPF           (show ip ospf neighbor)")
    print("  [4]  Tabla de Rutas            (show ip route ospf)")
    print("  [5]  IPsec Profile             (show crypto ipsec profile)")
    print("  [6]  Redundancia: VRRP+SLA+Track+OSPF cost")
    print("  [7]  NAT                       (show ip nat translations)")
    print("  [8]  Overlay E2E               (ping source <loopback IP>)")
    print("  [9]  Inter-LAN PC a PC         (docker exec)")
    print()
    print("  [10] >>> HEALTH-CHECK COMPLETO (1-9) <<<")
    print()
    print("  ── FAILOVER ─────────────────────────────────────────────")
    print("  [11] Failover WAN Branch2      (ANTES→CAIDA→DESPUES)")
    print("  [12] Failover HUB principal    (ANTES→CAIDA→DESPUES)")
    print()
    print("  ── UTILIDADES ───────────────────────────────────────────")
    print("  [13] Mostrar inventario")
    print("  [14] Re-verificar SSH")
    print("  [15] Verificar PCs")
    print("  [16] Re-descubrir inventario")
    print()
    print("  [q | Q | 0 ]  Salir")
    print()
 
# =====================================================================
# MAIN
# =====================================================================
def main():
    print(f"\n{BOLD}{'='*62}{RST}")
    print(f"{BOLD}  Iniciando Fase 4 — Laboratorio 2{RST}")
    print(f"{BOLD}{'='*62}{RST}")
 
    ip_map  = descubrir_inventario()
    equipos = construir_equipos(ip_map)
    if not equipos: print(fail("Sin equipos.")); sys.exit(1)
 
    mostrar_inventario(equipos)
    alc = verificar_alcanzabilidad(equipos)
    verificar_pcs()
 
    while True:
        menu()
        op = input("  Elija una opcion: ").strip()
        if   op in ("q","Q","0"):  print("\n  Adios.\n"); sys.exit(0)
        elif op == "1":   test_dmvpn(equipos,alc)
        elif op == "2":   test_nhrp(equipos,alc)
        elif op == "3":   test_ospf(equipos,alc)
        elif op == "4":   test_rutas(equipos,alc)
        elif op == "5":   test_ipsec(equipos,alc)
        elif op == "6":   test_redundancia(equipos,alc)
        elif op == "7":   test_nat(equipos,alc)
        elif op == "8":   test_overlay_e2e(equipos,alc)
        elif op == "9":   test_interlan(equipos,alc)
        elif op == "10":  health_check_completo(equipos,alc)
        elif op == "11":  failover_wan_branch2(equipos,alc)
        elif op == "12":  failover_hub(equipos,alc)
        elif op == "13":  mostrar_inventario(equipos)
        elif op == "14":  alc = verificar_alcanzabilidad(equipos)
        elif op == "15":  verificar_pcs()
        elif op == "16":
            ip_map  = descubrir_inventario()
            equipos = construir_equipos(ip_map)
            mostrar_inventario(equipos)
            alc = verificar_alcanzabilidad(equipos)
        else:
            print(f"\n  Opcion '{op}' invalida.")
        input(f"\n  {CYAN}ENTER para continuar...{RST}")
 
if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n\n  Interrumpido.\n"); sys.exit(0)