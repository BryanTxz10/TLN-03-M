config_interfaces = [
    "vlan 10",
    "Cliente A",
    "interface e0/1",
    "description Conexion con PE1",
    "switchport trunk encapsulation dot1q",
    "switchport mode trunk",
    "switchport trunk allowed vlan add 10",
    "interface e0/2",
    "description Conexion con Cliente A",
    "switchport mode access",
    "switchport access vlan 10"
]