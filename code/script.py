import json

base_config = [
"version 15.2",
"service timestamps debug datetime msec",
"service timestamps log datetime msec",
 #hostname
"boot-start-marker",
"boot-end-marker",

"no aaa new-model",
"no ip icmp rate-limit unreachable",
"ip cef",

"no ip domain lookup",
"ipv6 unicast-routing",
"ipv6 cef",

"multilink bundle-name authenticated",

"ip tcp synwait-time 5",

"ip forward-protocol nd",

"no ip http server",
"no ip http secure-server",

"control-plane",

"line con 0",
" exec-timeout 0 0",
" privilege level 15",
" logging synchronous",
" stopbits 1",
"line aux 0",
" exec-timeout 0 0",
" privilege level 15",
" logging synchronous",
" stopbits 1",
"line vty 0 4",
" login",

"end"]


def read_json(file_link):
    with open(file_link, 'r') as file:
        donnees_json = json.load(file)
    return donnees_json

def addressing(topology):
    for AS in topology:
        base_router_ip = topology[AS]['address']
        i = 1
        subnet_dict = give_subnet_number(topology[AS]["routers"])
        for router in topology[AS]['routers']:
            
            give_ipv6(AS, router, topology, subnet_dict)
            i+=1


        
        #faire modulo pour eviter i = 257
        #router et x

def insert_cfg_line(router, line, data):
    with open(f'i{router}_startup-config.cfg', 'r') as file:
        lines = file.readlines()
        lines.insert(line, data)
    with open(f'i{router}_startup-config.cfg', 'w') as file:
        file.writelines(lines)


def create_base_cfg(router, base_config):
    x = router[1:]
    with open(f'i{x}_startup-config.cfg', 'w') as file:
        for entry in base_config:
            file.write(entry + '\n')
        file.close()
    insert_cfg_line(x, 3, f"hostname {router}\n")

def create_interfaces_cfg(router, as_topology, subnet_dict):
    index_line = 1
    x = router[1:]
    with open(f'i{x}_startup-config.cfg', 'r') as file:
        lines = file.readline()
        while lines != "ip tcp synwait-time 5\n":
            lines = file.readline()
            index_line += 1

    for interface in as_topology['routers'][router].keys():

        insert_cfg_line(x, index_line, f"interface {as_topology['routers'][router][interface]}\n no ip address\n negotiation auto\n")
        index_line += 3
        if router[1:] < interface[1:]:
            subnet_index = subnet_dict[(router, interface)]
            router_index = 1  
        else:
            subnet_index = subnet_dict[(interface, router)]
            router_index = 2
        print(router, interface, subnet_index)

        insert_cfg_line(x, index_line, f" ipv6 address {as_topology['address']}{subnet_index}::{router_index}{as_topology['subnet_mask']}\n ipv6 enable\n")

        index_line += 2


def give_subnet_number(as_topology):
    #Cree les subnet pour une AS
    subnet_number = 1
    subnet_dict = dict()
    for router in as_topology:
        for key in as_topology[router]:
            if router[1:] < key[1:]:
                subnet_dict[(router, key)] = subnet_number
                subnet_number += 1
    print(subnet_dict)
    return subnet_dict           

def give_ipv6(as_number, router, topology, subnet_dict):
    x = router[1:]
    create_base_cfg(router, base_config)
    create_interfaces_cfg(router, topology[as_number], subnet_dict)

topology = read_json("intents.json")

addressing(topology)