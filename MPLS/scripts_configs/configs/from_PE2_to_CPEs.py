config_vrf = [
    "vrf definition A",
    "rd 10:10",
    "route-target both 10:10",
    "address-family ipv4",
    "exit-address-family",
    "address-family ipv6",
    "exit-address-family"
]

config_routing = [
    "ip route vrf A 192.168.20.0 255.255.255.0 10.0.2.2",
    "ipv6 route vrf A 2001:192:168:20::/64 Ethernet1/0.10 FC20::2",
    "router bgp 100",
    "address-family vpnv4",
    "neighbor 172.16.1.5 activate",
    "neighbor 172.16.1.5 send-community both",
    "neighbor 172.16.1.6 activate",
    "neighbor 172.16.1.6 send-community both",
    "address-family vpnv6",
    "neighbor 172.16.1.5 activate",
    "neighbor 172.16.1.5 send-community extended",
    "neighbor 172.16.1.6 activate",
    "neighbor 172.16.1.6 send-community extended",
    "address-family ipv4 vrf A",
    "redistribute static",
    "address-family ipv6 vrf A",
    "redistribute static"
]

config_int_cpes = [
    "interface e1/0",
    "description Conexion con SW Acceso 2",
    "no ip address",
    "no shutdown",
    "interface e1/0.10",
    "description Conexion con Cliente A",
    "vrf forwarding A",
    "encapsulation dot1q 10",
    "ip address 10.0.2.1 255.255.255.252",
    "ipv6 address FC20::1/64",
    "no shutdown"
]