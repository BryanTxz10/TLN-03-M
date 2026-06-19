from netmiko import ConnectHandler
import csv
import datetime

ROUTERS = [
    "clab-MPLS-PE1", "clab-MPLS-PE2",
    "clab-MPLS-P1",  "clab-MPLS-P2",
    "clab-MPLS-RR1", "clab-MPLS-RR2",
]

COMMANDS = [
    "show version",
    "show ip ospf neighbor",
    "show bgp vpnv4 unicast all summary",
    "show mpls ldp neighbor",
]

rows = []
for host in ROUTERS:
    device = {
        "device_type": "cisco_ios",
        "host":        host,
        "username":    "admin",
        "password":    "admin",
    }
    nombre = host.split("-")[-1]
    conn = ConnectHandler(**device)
    for cmd in COMMANDS:
        output = conn.send_command(cmd)
        rows.append({
            "router":  nombre,
            "comando": cmd,
            "output":  output.replace("\n", " | ")[:300]
        })
    conn.disconnect()

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
fname = f"reportes/estado_red_{ts}.csv"
with open(fname, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["router","comando","output"])
    writer.writeheader()
    writer.writerows(rows)
print(f"CSV generado: {fname}")
