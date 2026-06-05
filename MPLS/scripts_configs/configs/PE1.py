config_interfaces = [
    "interface lo0",
    "ip address 172.16.1.1 255.255.255.255",
    "mpls ip",
    "interface e0/1",
    "description Conexion con RR1",
    "ip address 10.0.0.1 255.255.255.252",
    "ip ospf network point-to-point",
    "mpls ip",
    "no shutdown",
    "interface e0/2",
    "description Conexion con P1",
    "ip address 10.0.0.5 255.255.255.252",
    "ip ospf network point-to-point",
    "mpls ip",
    "no shutdown",
    "interface e0/3",
    "description Conexion con P2",
    "ip address 10.0.0.9 255.255.255.252",
    "ip ospf network point-to-point",
    "mpls ip",
    "no shutdown"
]

config_igp = [
    "router ospf 10",
    "network 172.16.1.1 0.0.0.0 area 0",
    "network 10.0.0.0 0.0.0.3 area 0",
    "network 10.0.0.4 0.0.0.3 area 0",
    "network 10.0.0.8 0.0.0.3 area 0"
]

config_bgp = [
    "router bgp 100",
    "bgp router-id interface lo0",
    "no bgp default ipv4-unicast",
    "neighbor 172.16.1.5 remote-as 100",
    "neighbor 172.16.1.5 update-source lo0",
    "neighbor 172.16.1.6 remote-as 100",
    "neighbor 172.16.1.6 update-source lo0",
    "address-family ipv4 unicast",
    "neighbor 172.16.1.5 activate",
    "neighbor 172.16.1.6 activate"
]