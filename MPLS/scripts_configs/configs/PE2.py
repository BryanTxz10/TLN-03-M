config_mpls = [
    "mpls lsr-id 172.16.1.2",
    "mpls",
    "mpls ldp"
]

config_interfaces = [
    "interface lo0",
    "ip address 172.16.1.2 255.255.255.255",
    "mpls ip",
    "interface e0/1",
    "description Conexion con P1",
    "ip ospf network point-to-point",
    "ip address 10.0.0.30 255.255.255.252",
    "mpls ip",
    "no shutdown",
    "interface e0/2",
    "description Conexion con P2",
    "ip ospf network point-to-point",
    "ip address 10.0.0.34 255.255.255.252",
    "mpls ip",
    "no shutdown",
    "interface e0/3",
    "description Conexion con RR2",
    "ip ospf network point-to-point",
    "ip address 10.0.0.38 255.255.255.252",
    "no shutdown",
    "mpls ip"
]

config_igp = [
    "router ospf 10",
    "network 172.16.1.2 0.0.0.0 area 0",
    "network 10.0.0.28 0.0.0.3 area 0",
    "network 10.0.0.32 0.0.0.3 area 0",
    "network 10.0.0.36 0.0.0.3 area 0"
]

config_bgp = [
    "router bgp 100",
    "bgp router-id interface lo0",
    "no bgp default ipv4-unicast",
    "neighbor 172.16.1.5 remote-as 100",
    "neighbor 172.16.1.5 update-source Lo0",
    "neighbor 172.16.1.6 remote-as 100",
    "neighbor 172.16.1.6 update-source Lo0",
    "address-family ipv4 unicast",
    "neighbor 172.16.1.5 activate",
    "neighbor 172.16.1.6 activate"
]