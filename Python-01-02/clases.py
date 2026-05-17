#!/usr/bin/python3
class router(object):
        def __init__(self,name,interface_number,vendor):
                self.name= name
                self.interface_number = interface_number
                self.vendor = vendor
r1 = router("CISCO1", 10, "cisco")
r2 = router("JUN1", 20, "junos")

print(r1.name)
print(r2.interface_number)