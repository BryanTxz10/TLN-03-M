#!/usr/bin/env python3
"""
================================================================================
  LAB 2 - TEST SSH PARAMIKO
  Prueba exec_command() e invoke_shell() en todos los nodos
  (Basado en el método del profesor, pero generalizado)
================================================================================
"""
 
import paramiko
import time
import sys
 
# Todos los nodos con SSH (sin PCs linux)
NODES = {
    # HUBs
    "CPE-HQ":         "clab-ISP-TDP-CLARO-IOL-CPE-HQ",
    "CPE-HQ-BK":      "clab-ISP-TDP-CLARO-IOL-CPE-HQ-BK",
    # Branch1
    "CPE-BRANCH":     "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH",
    "CPE-BRANCH-BK":  "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH-BK",
    # Branch2 (NUEVOS)
    "CPE-BRANCH2":    "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2",
    "CPE-BRANCH2-BK": "clab-ISP-TDP-CLARO-IOL-CPE-BRANCH2-BK",
    # Movistar
    "M1": "clab-ISP-TDP-CLARO-IOL-M1",
    "M2": "clab-ISP-TDP-CLARO-IOL-M2",
    "M3": "clab-ISP-TDP-CLARO-IOL-M3",
    "M4": "clab-ISP-TDP-CLARO-IOL-M4",
    # Claro
    "C1": "clab-ISP-TDP-CLARO-IOL-C1",
    "C2": "clab-ISP-TDP-CLARO-IOL-C2",
    "C3": "clab-ISP-TDP-CLARO-IOL-C3",
    "C4": "clab-ISP-TDP-CLARO-IOL-C4",
    "C5": "clab-ISP-TDP-CLARO-IOL-C5",
    # Telxius
    "T1": "clab-ISP-TDP-CLARO-IOL-T1",
    "T2": "clab-ISP-TDP-CLARO-IOL-T2",
    "T3": "clab-ISP-TDP-CLARO-IOL-T3",
    # ATT
    "ATT1": "clab-ISP-TDP-CLARO-IOL-ATT1",
    "ATT2": "clab-ISP-TDP-CLARO-IOL-ATT2",
    "ATT3": "clab-ISP-TDP-CLARO-IOL-ATT3",
    # Orange
    "OR1": "clab-ISP-TDP-CLARO-IOL-OR1",
    "OR2": "clab-ISP-TDP-CLARO-IOL-OR2",
    "OR3": "clab-ISP-TDP-CLARO-IOL-OR3",
    # Lumen
    "LU1": "clab-ISP-TDP-CLARO-IOL-LU1",
    "LU2": "clab-ISP-TDP-CLARO-IOL-LU2",
    "LU3": "clab-ISP-TDP-CLARO-IOL-LU3",
    # Google
    "GOOGLE": "clab-ISP-TDP-CLARO-IOL-GOOGLE",
    # Switches L2
    "SW-PISO1":    "clab-ISP-TDP-CLARO-IOL-SW-PISO1",
    "SW-PISO2":    "clab-ISP-TDP-CLARO-IOL-SW-PISO2",
    "SW-R-PISO1":  "clab-ISP-TDP-CLARO-IOL-SW-R-PISO1",
    "SW-R-PISO2":  "clab-ISP-TDP-CLARO-IOL-SW-R-PISO2",
    "SW-R2-PISO1": "clab-ISP-TDP-CLARO-IOL-SW-R2-PISO1",
}
 
username = "admin"
password = "admin"
 
results = {}
 
print("\n" + "="*70)
print("  LAB 2 - TEST SSH PARAMIKO (exec_command + invoke_shell)")
print("="*70 + "\n")
 
# ──────────────────────────────────────────────────────────────────────────────
# TEST CADA NODO
# ──────────────────────────────────────────────────────────────────────────────
 
for node_name, container_name in NODES.items():
    print(f"  [{node_name:<20}]", end=" ", flush=True)
    
    exec_ok = False
    shell_ok = False
    error_msg = ""
    
    # ── EXEC_COMMAND (pc2.md Parte 4) ─────────────────────────────────────
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    
    try:
        ssh_client.connect(hostname=container_name,
                           username=username,
                           password=password,
                           look_for_keys=False,
                           timeout=10)
        
        stdin, stdout, stderr = ssh_client.exec_command("show version | include hostname")
        time.sleep(0.5)
        output = stdout.read().decode()
        exec_ok = True
        print("✓", end=" ", flush=True)
        
        ssh_client.close()
    except Exception as e:
        error_msg = str(e)[:50]
        print("✗", end=" ", flush=True)
    
    # ── INVOKE_SHELL (pc2.md Parte 3) ─────────────────────────────────────
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    
    try:
        ssh_client.connect(hostname=container_name,
                           username=username,
                           password=password,
                           look_for_keys=False,
                           timeout=10)
        
        shell = ssh_client.invoke_shell()
        time.sleep(1.2)
        if shell.recv_ready():
            shell.recv(4096)
        shell.send("terminal length 0\n")
        time.sleep(0.5)
        shell.send("show clock\n")
        time.sleep(1)
        if shell.recv_ready():
            shell.recv(2048)
        shell_ok = True
        print("✓", end=" ", flush=True)
        
        ssh_client.close()
    except Exception as e:
        if not error_msg:
            error_msg = str(e)[:50]
        print("✗", end=" ", flush=True)
    
    # ── ESTADO ───────────────────────────────────────────────────────────
    if exec_ok and shell_ok:
        print("LISTO")
    else:
        print(f"FAIL ({error_msg})")
    
    # ── GUARDAR RESULTADO ──────────────────────────────────────────────────
    results[node_name] = {
        "exec": exec_ok,
        "shell": shell_ok,
        "ready": exec_ok and shell_ok,
        "error": error_msg
    }
 
# ──────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ──────────────────────────────────────────────────────────────────────────────
 
print("\n" + "="*70)
print("  RESUMEN")
print("="*70 + "\n")
 
print(f"  {'NODO':<20} {'exec_cmd':<12} {'invoke_shell':<15} ESTADO")
print("  " + "-"*68)
 
ready_nodes = []
problem_nodes = []
 
for node_name, res in sorted(results.items()):
    exec_s = "✓ OK" if res["exec"] else "✗ FAIL"
    shell_s = "✓ OK" if res["shell"] else "✗ FAIL"
    
    if res["ready"]:
        estado = "✓ LISTO"
        ready_nodes.append(node_name)
        tag = " ★" if "BRANCH2" in node_name else ""
    else:
        estado = "✗ NO LISTO"
        problem_nodes.append(node_name)
        tag = ""
    
    print(f"  {node_name:<20} {exec_s:<12} {shell_s:<15} {estado}{tag}")
    
    if res["error"]:
        print(f"    Error: {res['error']}")
 
print("\n" + "="*70)
print(f"  RESULTADO: {len(ready_nodes)}/{len(NODES)} nodos listos")
print("="*70)
 
if ready_nodes:
    print(f"\n  ✓ Listos ({len(ready_nodes)}):")
    for n in ready_nodes[:10]:
        tag = " ★ BRANCH2" if "BRANCH2" in n else ""
        print(f"    {n}{tag}")
    if len(ready_nodes) > 10:
        print(f"    ... y {len(ready_nodes)-10} más")
 
if problem_nodes:
    print(f"\n  ✗ Con problemas ({len(problem_nodes)}):")
    for n in problem_nodes[:10]:
        print(f"    {n}")
    if len(problem_nodes) > 10:
        print(f"    ... y {len(problem_nodes)-10} más")
 
# ── Estado especial Branch2 ────────────────────────────────────────────────
b2_ok = results.get("CPE-BRANCH2", {}).get("ready", False)
b2bk_ok = results.get("CPE-BRANCH2-BK", {}).get("ready", False)
 
print("\n" + "-"*70)
if b2_ok and b2bk_ok:
    print("  ✓✓ CPE-BRANCH2 y CPE-BRANCH2-BK → LISTOS para verificador")
    sys.exit(0)
else:
    print("  ⚠ Revisar CPE-BRANCH2 / CPE-BRANCH2-BK antes de continuar")
    sys.exit(1)