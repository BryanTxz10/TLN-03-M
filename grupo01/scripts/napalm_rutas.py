from napalm import get_network_driver
import json

driver = get_network_driver("ios")

device = driver(
    hostname="clab-MPLS-PE1",
    username="admin",
    password="admin",
    optional_args={
        "disabled_algorithms": {
            "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
        }
    }
)

device.open()
print("=== Rutas hacia red Sede 2 (192.168.20.0/24) ===")
rutas = device.get_route_to(destination="192.168.20.0/24")
print(json.dumps(rutas, indent=2))
device.close()
