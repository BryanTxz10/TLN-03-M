config_interfaces = [
    "interface e0/1",
    "description Conexion con PE2",
    "ip address 10.0.2.2 255.255.255.252",
    "ipv6 add FC20::2/64",
    "no shutdown",
    "interface e0/2",
    "description Conexion con LAN",
    "ip address 192.168.20.1 255.255.255.0",
    "ipv6 address 2001:192:168:20::1/64",
    "no shutdown"
]

config_routing = [
    "ip route 192.168.10.0 255.255.255.0 10.0.2.1",
    "ipv6 route 2001:192:168:10::/64 FC20::1"
]