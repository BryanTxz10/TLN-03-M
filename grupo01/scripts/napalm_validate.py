from napalm import get_network_driver
import json
import datetime

ROUTERS = [
    {"hostname": "clab-MPLS-PE1", "nombre": "PE1"},
    {"hostname": "clab-MPLS-PE2", "nombre": "PE2"},
    {"hostname": "clab-MPLS-P1",  "nombre": "P1"},
    {"hostname": "clab-MPLS-P2",  "nombre": "P2"},
    {"hostname": "clab-MPLS-RR1", "nombre": "RR1"},
    {"hostname": "clab-MPLS-RR2", "nombre": "RR2"},
]

driver = get_network_driver("ios")
reporte = []

for r in ROUTERS:
    print(f"Conectando a {r['nombre']}...")
    device = driver(
        hostname=r["hostname"],
        username="admin",
        password="admin",
        optional_args={
            "disabled_algorithms": {
                "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
            }
        }
    )
    device.open()

    facts      = device.get_facts()
    interfaces = device.get_interfaces()
    ips        = device.get_interfaces_ip()
    bgp        = device.get_bgp_neighbors()

    try:
        environment = device.get_environment()
        cpu_usage = list(environment.get("cpu", {}).values())[0].get("%usage", "N/A")
    except Exception:
        environment = "No disponible en IOL"
        cpu_usage = "N/A"

    activas     = sum(1 for v in interfaces.values() if v["is_up"])
    vecinos_bgp = len(bgp.get("global", {}).get("peers", {}))

    reporte.append({
        "router":             r['nombre'],
        "hostname":           facts["hostname"],
        "modelo":             facts["model"],
        "version_ios":        facts["os_version"],
        "interfaces_activas": activas,
        "vecinos_bgp":        vecinos_bgp,
        "cpu_usage":          cpu_usage,
        "environment":        environment if isinstance(environment, str) else "OK",
        "estado":             "OK"
    })

    device.close()

print("\n" + "="*50)
print("REPORTE NAPALM - MPLS L3VPN")
print("="*50)
for item in reporte:
    print(f"Router:             {item['router']}")
    print(f"Hostname:           {item['hostname']}")
    print(f"Modelo:             {item['modelo']}")
    print(f"Version IOS:        {item['version_ios']}")
    print(f"Interfaces activas: {item['interfaces_activas']}")
    print(f"Vecinos BGP:        {item['vecinos_bgp']}")
    print(f"CPU Usage:          {item['cpu_usage']}")
    print(f"Environment:        {item['environment']}")
    print(f"Estado:             {item['estado']}")
    print("-"*50)

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
with open(f"reportes/napalm_{ts}.json", "w") as f:
    json.dump(reporte, f, indent=2)
print(f"\nReporte guardado en reportes/napalm_{ts}.json")
