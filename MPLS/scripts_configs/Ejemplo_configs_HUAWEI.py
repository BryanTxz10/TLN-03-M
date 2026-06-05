# Netmiko example: Retrieve the same info with simplified interface
from netmiko import ConnectHandler
#
device = {
    'device_type': 'huawei',
    'host': 'clab-Branch-HUAWEI',
    'username': 'admin',
    'password': 'admin',
    'session_log': 'huawei-log.txt',
}
#
net_connect = ConnectHandler(**device)
#
config_int_LAN = ['interface Ethernet1/0/0', 
                  'description LAN - Realizado via Python - Netmiko', 
                  'ip address 192.168.1.3 24',
                  'undo shutdown',
                  'vrrp vrid 10 virtual-ip 192.168.1.1',
                  'vrrp vrid 10 priority 90']

config_int_WAN = ['interface Ethernet1/0/1', 
                  'description WAN - Realizado via Python - Netmiko', 
                  'ip address 10.0.0.6 30',
                  'undo shutdown']

config_int_Lo0 = ['interface LoopBack0', 
                  'description LoopBack0 - Realizado via Python - Netmiko', 
                  'ip address 200.0.0.1 24']

print('\nConfigurando Hostname')
config_nombre = net_connect.send_config_set('sysname R-HUAWEI', 
                                       strip_command=False,cmd_verify=False, 
                                       exit_config_mode=False)
print(f'\nConfigurando Interface LAN {config_int_LAN[0]}')
conf_int_LAN = net_connect.send_config_set(config_int_LAN, 
                                       strip_command=False,cmd_verify=False, 
                                       exit_config_mode=False)
print(f'\nConfigurando Interface WAN {config_int_WAN[0]}')
conf_int_LAN = net_connect.send_config_set(config_int_WAN, 
                                       strip_command=False,cmd_verify=False, 
                                       exit_config_mode=False)
print(f'\nConfigurando Interface LoopBack0 {config_int_Lo0[0]}')
conf_int_Lo0 = net_connect.send_config_set(config_int_Lo0, 
                                       strip_command=False,cmd_verify=False, 
                                       exit_config_mode=False)
print(f'\nConfigurando Default Gateway')
config_default_route = net_connect.send_config_set('ip route-static 0.0.0.0 0.0.0.0 10.0.0.5',
                                                   strip_command=False,cmd_verify=False,exit_config_mode=False)
print(f'\nGuardando Configuración')
commit_ = net_connect.send_command_timing('commit', strip_command=False)
return_ = net_connect.send_command_timing('return', strip_command=False)
#
save_ = net_connect.send_command_timing('save', strip_command=False)

if 'Y/N' in save_:
    output_5 = net_connect.send_command_timing(
        'Y',
        strip_command=False)
#
net_connect.disconnect()