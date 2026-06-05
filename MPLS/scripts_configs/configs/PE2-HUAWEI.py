config_mpls = [
    "mpls lsr-id 172.16.1.2",
    "mpls",
    "mpls ldp"
]

config_interfaces = [
    "interface lo0",
    "ip address 172.16.1.2 32",
    "mpls",
    "mpls ip",
    "interface Ethernet1/0/0",
    "description Conexion con P1",
    "ospf network-type p2p",
    "ip address 10.0.0.30 30",
    "mpls",
    "mpls ldp",
    "interface Ethernet1/0/1",
    "description Conexion con P2",
    "ospf network-type p2p",
    "ip address 10.0.0.34 30",
    "mpls",
    "mpls ldp",
    "interface Ethernet1/0/2",
    "description Conexion con RR2",
    "ospf network-type p2p",
    "ip address 10.0.0.38 30",
    "mpls",
    "mpls ldp"
]

config_igp = [
    "ospf 10",
    "area 0",
    "network 172.16.1.2 0.0.0.0",
    "network 10.0.0.28 0.0.0.3",
    "network 10.0.0.32 0.0.0.3",
    "network 10.0.0.36 0.0.0.3"
]

config_bgp = [
    "bgp 100",
    "router-id 172.16.1.2",
    "undo default ipv4-unicast",
    "peer 172.16.1.5 as-number 100",
    "peer 172.16.1.5 connect-interface LoopBack0",
    "peer 172.16.1.6 as-number 100",
    "peer 172.16.1.6 connect-interface LoopBack0",
    "ipv4-family unicast",
    "peer 172.16.1.5 enable",
    "peer 172.16.1.6 enable"
]