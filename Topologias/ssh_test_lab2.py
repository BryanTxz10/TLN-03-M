#!/usr/bin/env python3
"""
================================================================================
  LABORATORIO 2 – TEST DE CONECTIVIDAD SSH
  Conexión por NOMBRE de contenedor (método del profesor) + fallback IP
================================================================================
 
  POR QUÉ POR NOMBRE Y NO POR IP:
  ───────────────────────────────────
  El profesor se conecta así:
      r1 = "clab-lab-iol-2r-r1"
      ssh_client.connect(hostname=r1, ...)
 
  Containerlab registra los nombres de los contenedores y Docker los
  resuelve por DNS interno. La IP cambia cada vez que redesplegas el lab,
  pero el NOMBRE es estable. Por eso conectar por nombre es lo correcto.
 
  Formato del nombre:  clab-<LAB_NAME>-<NODO>
  Tu lab:              clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2
  ⚠️ OJO: el nombre del lab va en MAYÚSCULAS (tal como en el .yml: name:)
 
  Este script:
    1. Prueba conexión por NOMBRE (como el profesor)
    2. Si el nombre no resuelve, intenta por IP (obtenida de docker)
    3. Prueba exec_command() e invoke_shell()
    4. Genera inventario_lab2.py para el verificador
================================================================================
"""
 
import subprocess
import json
import socket
import paramiko
import time
import sys
import datetime
 
# ──────────────────────────────────────────────────────────────────────────────
# COLORES
# ──────────────────────────────────────────────────────────────────────────────
try:
    import colorama
    colorama.init(autoreset=True)
    GREEN  = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
    CYAN   = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"; BLUE = "\033[94m"
except ImportError:
    GREEN = RED = YELLOW = CYAN = BOLD = RESET = BLUE = ""
 
# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────
# Nombre del lab EXACTO como aparece en clab inspect (MAYÚSCULAS)
LAB_NAME    = "ISP-TDP-CLARO-IOL"
CLAB_PREFIX = f"clab-{LAB_NAME}"          # → clab-ISP-TDP-CLARO-IOL
 
SSH_USER    = "admin"
SSH_PASS    = "admin"
SSH_PORT    = 22
SSH_TIMEOUT = 10
 
# Nodos con SSH (routers y switches IOL). Las PCs linux se excluyen.
SSH_NODES = [
    # HUBs
    "CPE-HQ", "CPE-HQ-BK",
    # Branch1
    "CPE-BRANCH", "CPE-BRANCH-BK",
    # Branch2 (NUEVOS - foco del lab)
    "CPE-BRANCH2", "CPE-BRANCH2-BK",
    # Movistar
    "M1", "M2", "M3", "M4",
    # Claro
    "C1", "C2", "C3", "C4", "C5",
    # Telxius
    "T1", "T2", "T3",
    # ATT
    "ATT1", "ATT2", "ATT3",
    # Orange
    "OR1", "OR2", "OR3",
    # Lumen
    "LU1", "LU2", "LU3",
    # Google
    "GOOGLE",
    # Switches L2
    "SW-PISO1", "SW-PISO2", "SW-R-PISO1", "SW-R-PISO2", "SW-R2-PISO1",
]
 
BRANCH2_NODES = ["CPE-BRANCH2", "CPE-BRANCH2-BK"]
CPE_NODES = ["CPE-HQ", "CPE-HQ-BK", "CPE-BRANCH", "CPE-BRANCH-BK",
             "CPE-BRANCH2", "CPE-BRANCH2-BK"]
 
 
def container_name(node: str) -> str:
    """clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2  (nombre como el profesor)"""
    return f"{CLAB_PREFIX}-{node}"
 
 
# ──────────────────────────────────────────────────────────────────────────────
# OBTENER IP REAL (fallback si el nombre no resuelve por DNS)
# ──────────────────────────────────────────────────────────────────────────────
 
def get_ip_from_docker(node: str) -> str:
    """
    Fallback: obtiene la IP real del contenedor desde docker inspect.
    Solo se usa si conectar por nombre falla.
    """
    cname = container_name(node)
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f",
             "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", cname],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            ips = r.stdout.strip().split()
            return ips[0] if ips else None
    except Exception:
        pass
    return None
 
 
def list_lab_containers() -> dict:
    """Mapea nombre de nodo → estado, leyendo docker ps."""
    out = {}
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if not parts or CLAB_PREFIX not in parts[0]:
                continue
            cname = parts[0]
            status = parts[1] if len(parts) > 1 else "?"
            node = cname.replace(f"{CLAB_PREFIX}-", "")
            out[node] = {"container": cname, "status": status}
    except Exception:
        pass
    return out
 
 
# ──────────────────────────────────────────────────────────────────────────────
# TESTS SSH (por nombre primero, luego por IP)
# ──────────────────────────────────────────────────────────────────────────────
 
def resolve_hostname(name: str) -> bool:
    """Verifica si el nombre del contenedor resuelve por DNS."""
    try:
        socket.gethostbyname(name)
        return True
    except socket.error:
        return False
 
 
def port_open(host: str, port: int = 22, timeout: int = 3) -> bool:
    try:
        s = socket.socket()
        s.settimeout(timeout)
        ok = s.connect_ex((host, port)) == 0
        s.close()
        return ok
    except Exception:
        return False
 
 
def make_client() -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.load_system_host_keys()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return c
 
 
def test_exec_command(host: str) -> tuple:
    """
    exec_command() — método de VERIFICACIÓN (pc2.md Parte 4).
    Igual que el ejemplo del profesor (02-cisco-ssh.py).
    """
    client = make_client()
    try:
        client.connect(
            hostname=host, port=SSH_PORT,
            username=SSH_USER, password=SSH_PASS,
            look_for_keys=False, allow_agent=False,
            timeout=SSH_TIMEOUT,
        )
        stdin, stdout, stderr = client.exec_command("show version | include uptime")
        time.sleep(0.6)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        client.close()
        return True, (out[:55] if out else "(conectado, sin output)")
    except paramiko.AuthenticationException:
        return False, "auth fallida (admin/admin?)"
    except paramiko.SSHException as e:
        return False, f"SSHException: {str(e)[:45]}"
    except socket.timeout:
        return False, "timeout"
    except socket.gaierror:
        return False, "nombre no resuelve (DNS)"
    except Exception as e:
        return False, str(e)[:55]
 
 
def test_invoke_shell(host: str) -> tuple:
    """
    invoke_shell() — método de CONFIGURACIÓN (pc2.md Parte 3).
    Igual que el ejemplo del profesor (01-cisco-ssh.py shell).
    """
    client = make_client()
    try:
        client.connect(
            hostname=host, port=SSH_PORT,
            username=SSH_USER, password=SSH_PASS,
            look_for_keys=False, allow_agent=False,
            timeout=SSH_TIMEOUT,
        )
        sh = client.invoke_shell()
        time.sleep(1.2)
        if sh.recv_ready():
            sh.recv(4096)
        sh.send("terminal length 0\n")
        time.sleep(0.4)
        sh.send("show clock\n")
        time.sleep(0.8)
        out = sh.recv(2048).decode("utf-8", errors="replace").strip() if sh.recv_ready() else "(OK)"
        client.close()
        return True, out[:55]
    except paramiko.AuthenticationException:
        return False, "auth fallida"
    except socket.gaierror:
        return False, "nombre no resuelve (DNS)"
    except Exception as e:
        return False, str(e)[:55]
 
 
# ──────────────────────────────────────────────────────────────────────────────
# CHECK COMPLETO POR NODO
# ──────────────────────────────────────────────────────────────────────────────
 
def check_node(node: str, containers: dict) -> dict:
    cname = container_name(node)
    result = {
        "node": node, "container": cname,
        "status": containers.get(node, {}).get("status", "no encontrado"),
        "connect_via": None, "target": None,
        "exec_ok": False, "shell_ok": False, "ready": False, "note": ""
    }
 
    print(f"\n  {BOLD}[ {node} ]{RESET}")
    print(f"    Contenedor: {CYAN}{cname}{RESET}")
 
    # ¿El contenedor existe y corre?
    if node not in containers:
        print(f"    {RED}✗ Contenedor no encontrado en docker ps{RESET}")
        result["note"] = "contenedor inexistente"
        return result
    if "Up" not in result["status"]:
        print(f"    {YELLOW}⚠ Estado: {result['status']}{RESET}")
 
    # ── INTENTO 1: por NOMBRE (como el profesor) ─────────────────────────────
    name_resolves = resolve_hostname(cname)
    if name_resolves:
        print(f"    {GREEN}✓{RESET} Nombre resuelve por DNS")
        target = cname
        result["connect_via"] = "nombre"
    else:
        print(f"    {YELLOW}~{RESET} Nombre NO resuelve por DNS, usando IP como fallback")
        ip = get_ip_from_docker(node)
        if not ip:
            print(f"    {RED}✗ Tampoco se pudo obtener IP desde docker{RESET}")
            result["note"] = "ni nombre ni IP disponibles"
            return result
        print(f"    {GREEN}✓{RESET} IP obtenida: {CYAN}{ip}{RESET}")
        target = ip
        result["connect_via"] = "ip"
 
    result["target"] = target
 
    # ── Puerto 22 ────────────────────────────────────────────────────────────
    if not port_open(target):
        print(f"    {RED}✗ Puerto 22 cerrado en {target}{RESET}")
        result["note"] = "puerto 22 cerrado (IOS aún iniciando?)"
        return result
    print(f"    {GREEN}✓{RESET} Puerto 22 abierto")
 
    # ── exec_command ─────────────────────────────────────────────────────────
    ok_e, msg_e = test_exec_command(target)
    result["exec_ok"] = ok_e
    icon = f"{GREEN}✓{RESET}" if ok_e else f"{RED}✗{RESET}"
    print(f"    {icon} exec_command()  → {msg_e}")
 
    # ── invoke_shell ─────────────────────────────────────────────────────────
    ok_s, msg_s = test_invoke_shell(target)
    result["shell_ok"] = ok_s
    icon = f"{GREEN}✓{RESET}" if ok_s else f"{RED}✗{RESET}"
    print(f"    {icon} invoke_shell()  → {msg_s}")
 
    result["ready"] = ok_e and ok_s
    if result["ready"]:
        print(f"    {GREEN}{BOLD}→ LISTO para Paramiko (vía {result['connect_via']}){RESET}")
    else:
        print(f"    {RED}{BOLD}→ NO listo{RESET}")
        result["note"] = msg_e if not ok_e else msg_s
 
    return result
 
 
# ──────────────────────────────────────────────────────────────────────────────
# RESUMEN Y EXPORTACIÓN
# ──────────────────────────────────────────────────────────────────────────────
 
def print_summary(results: list):
    print(f"\n{BOLD}{CYAN}{'═'*74}{RESET}")
    print(f"{BOLD}{CYAN}  RESUMEN{RESET}")
    print(f"{BOLD}{CYAN}{'═'*74}{RESET}\n")
 
    hdr = f"  {'NODO':<18}{'VÍA':<8}{'TARGET':<34}{'exec':<7}{'shell':<7}ESTADO"
    print(f"{BOLD}{hdr}{RESET}")
    print(f"  {'─'*72}")
 
    ready, problems = [], []
    for r in results:
        via    = r["connect_via"] or "—"
        target = (r["target"] or "—")[:32]
        e = f"{GREEN}OK{RESET}"  if r["exec_ok"]  else f"{RED}KO{RESET}"
        s = f"{GREEN}OK{RESET}"  if r["shell_ok"] else f"{RED}KO{RESET}"
        if r["ready"]:
            est = f"{GREEN}LISTO ✓{RESET}"; ready.append(r["node"])
        else:
            est = f"{RED}FALLO ✗{RESET}";  problems.append(r)
        tag = f" {GREEN}★{RESET}" if "BRANCH2" in r["node"] else ""
        print(f"  {r['node']:<18}{via:<8}{target:<34}{e:<14}{s:<14}{est}{tag}")
 
    print(f"\n  {GREEN}LISTOS: {len(ready)}{RESET}  →  {', '.join(ready) if ready else '—'}")
    if problems:
        print(f"  {RED}CON PROBLEMAS: {len(problems)}{RESET}  →  {', '.join(p['node'] for p in problems)}")
 
    # Estado Branch2
    b2  = next((r for r in results if r["node"] == "CPE-BRANCH2"), None)
    b2k = next((r for r in results if r["node"] == "CPE-BRANCH2-BK"), None)
    print(f"\n  {'─'*72}")
    if b2 and b2k and b2["ready"] and b2k["ready"]:
        print(f"  {GREEN}{BOLD}✓ Branch2 OK → ejecuta: python3 verificador_lab2.py{RESET}")
    elif b2 or b2k:
        print(f"  {YELLOW}{BOLD}~ Revisa Branch2 antes de ejecutar el verificador{RESET}")
 
    return ready, problems
 
 
def save_inventory(results: list):
    """Genera inventario_lab2.py con nombre de contenedor + IP de respaldo."""
    fname = "inventario_lab2.py"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# inventario_lab2.py — auto-generado por ssh_test_lab2.py ({ts})",
        f"# Importar en verificador_lab2.py:",
        f"#   from inventario_lab2 import DISCOVERED_INVENTORY",
        "",
        "DISCOVERED_INVENTORY = {",
    ]
    for r in results:
        if r["ready"] and r["target"]:
            lines.append(
                f'    "{r["node"]}": {{"host": "{r["target"]}", '
                f'"username": "admin", "password": "admin", '
                f'"via": "{r["connect_via"]}"}},'
            )
    lines += ["}", ""]
    with open(fname, "w") as f:
        f.write("\n".join(lines))
    print(f"\n  {GREEN}[✓]{RESET} Guardado → {BOLD}{fname}{RESET}")
 
 
def show_fixes(problems: list):
    if not problems:
        return
    print(f"\n{BOLD}{YELLOW}── SOLUCIÓN DE PROBLEMAS {'─'*48}{RESET}\n")
    for p in problems:
        print(f"  {BOLD}▸ {p['node']}{RESET} — {p['note']}")
        note = p["note"].lower()
        if "puerto 22" in note:
            print(f"    IOS aún arrancando. Espera 1-2 min y reintenta.")
            print(f"    Verifica por consola: {CYAN}docker attach {p['container']}{RESET}")
        elif "auth" in note:
            print(f"    Usuario/clave incorrectos. Confirma: admin / admin")
        elif "no resuelve" in note or "inexistente" in note:
            print(f"    El nombre no resuelve y no hay IP. Verifica el lab:")
            print(f"    {CYAN}sudo clab inspect -t Topologia-ISP.yml{RESET}")
        else:
            print(f"    Detalle: {p['note']}")
        print()
 
 
# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
 
def main():
    print(f"\n{BOLD}{CYAN}{'═'*74}{RESET}")
    print(f"{BOLD}{CYAN}  LAB 2 · TEST SSH (conexión por NOMBRE como el profesor){RESET}")
    print(f"{BOLD}{CYAN}  {LAB_NAME}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*74}{RESET}")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Prefijo de contenedor: {BOLD}{CLAB_PREFIX}-<NODO>{RESET}\n")
 
    while True:
        print(f"\n{BOLD}  ¿Qué verificar?{RESET}")
        print(f"  [1] Solo Branch2  (CPE-BRANCH2 + CPE-BRANCH2-BK)")
        print(f"  [2] Solo CPEs     (HQ + Branch1 + Branch2)")
        print(f"  [3] TODOS los nodos del lab")
        print(f"  [0] Salir")
 
        op = input("\n  Opción: ").strip()
        if op == "0":
            break
 
        sel = {"1": BRANCH2_NODES, "2": CPE_NODES, "3": SSH_NODES}.get(op)
        if sel is None:
            print(f"  {RED}Opción inválida{RESET}")
            continue
 
        containers = list_lab_containers()
        if not containers:
            print(f"\n  {RED}No se detectaron contenedores '{CLAB_PREFIX}-*'.{RESET}")
            print(f"  Verifica con: {CYAN}docker ps | grep {CLAB_PREFIX}{RESET}")
            print(f"  ¿El lab está desplegado? {CYAN}sudo clab deploy -t Topologia-ISP.yml{RESET}")
            continue
 
        print(f"\n  Contenedores del lab detectados: {GREEN}{len(containers)}{RESET}")
 
        results = [check_node(n, containers) for n in sel]
        ready, problems = print_summary(results)
        show_fixes(problems)
 
        if input("\n  ¿Guardar inventario? [s/N]: ").strip().lower() == "s":
            save_inventory(results)
        if input("  ¿Otra prueba? [s/N]: ").strip().lower() != "s":
            break
 
    print(f"\n  {CYAN}Listo.{RESET}\n")
 
 
if __name__ == "__main__":
    main()