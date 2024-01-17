import json
import sys

base_config = [
"version 15.2",
"service timestamps debug datetime msec",
"service timestamps log datetime msec",
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


def read_json(file_path):
    #Essaye de lire et extraire la topologie d'un json, sinon quitte le programme avec un message d'erreur
    try:
        with open(file_path, 'r') as file:
            topology = json.load(file)
    except FileNotFoundError:
        print("---------------------------------------------------------------------")
        print(f"Error : file {file_path} not found. You must be in the 'code' directory !")
        print("---------------------------------------------------------------------")
        sys.exit(1)
    except Exception:
        print(f"Error : {Exception}")
        sys.exit(1)
    return topology


def main(topology):
    #Pour chaque AS, configure l'adressage de toutes les interfaces des routeurs : ipv6 = {base_address}:{AS_index}{subnet_index}::{router_index}/{mask}
    for AS in topology:
        subnet_dict = give_subnet_number(topology[AS]["routers"])
        for router in topology[AS]['routers']:
            create_base_cfg(router, base_config)
            create_router_interfaces(router, topology[AS], subnet_dict)
            activate_protocols(router, topology[AS])


def insert_cfg_line(router, index_line, data):
    #insert une information 'data' à la ligne 'line'.
    with open(f'i{router[1:]}_startup-config.cfg', 'r') as file:
        lines = file.readlines()
        lines.insert(index_line, data)
    with open(f'i{router[1:]}_startup-config.cfg', 'w') as file:
        file.writelines(lines)


def create_base_cfg(router, base_config):
    #créer pour un routeur, son fichier cfg de base à partir d'une liste 'base config', et insert l'hostname.
    with open(f'i{router[1:]}_startup-config.cfg', 'w') as file:
        for entry in base_config:
            file.write(entry + '\n')
    insert_cfg_line(router, 3, f"hostname {router}\n")


def find_index(router, line):
    #Trouve l'indice correcte pour inserer une nouvelle ligne juste après la ligne 'line'.
    index_line = 1
    with open(f'i{router[1:]}_startup-config.cfg', 'r') as file:
        lines = file.readline()
        while lines != line:
            lines = file.readline()
            index_line += 1
    return index_line


def create_router_interfaces(router, as_topology, subnet_dict):
    #insert dans le cfg du routeur toutes les ses interfaces et leurs ipv6 correspondantes.
    index_line = find_index(router, line="ip tcp synwait-time 5\n")

    for neighbor in as_topology['routers'][router].keys():

        if router[1:] < neighbor[1:]:
            subnet_index = subnet_dict[(router, neighbor)]
            router_index = 1  
        else:
            subnet_index = subnet_dict[(neighbor, router)]
            router_index = 2

        insert_cfg_line(router, index_line, f"interface {as_topology['routers'][router][neighbor]}\n no ip address\n negotiation auto\n ipv6 address {as_topology['address']}{subnet_index}::{router_index}{as_topology['subnet_mask']}\n ipv6 enable\n")
        index_line += 5


def give_subnet_number(as_topology):
    #Creer un dictionnaire qui pour chaque arrête d'une AS, donne un numero de subnet : {(R1,R2):1, (R2,R3):2...}
    subnet_number = 1
    subnet_dict = dict()
    for router in as_topology:
        for neighbor in as_topology[router]:
            if router[1:] < neighbor[1:]:
                subnet_dict[(router, neighbor)] = subnet_number
                subnet_number += 1
    return subnet_dict

def is_rip(as_topology):
    #retourne True si RIP est à activer, False sinon.
    return True if as_topology["protocol"] == "RIP" else False

def is_ospf(as_topology):
    #retourne True si RIP est à activer, False sinon
    return True if as_topology["protocol"] == "OSPF" else False

def activate_protocols(router, as_topology):
    #active tous les protocols d'un routeur.
    router_id = give_router_id(router)
    if is_ospf(as_topology):
        activate_ospf(router, as_topology, router_id)
    elif is_rip(as_topology):
        activate_rip(router, as_topology)
    activate_bgp(router, as_topology)

def activate_ospf(router, as_topology, router_id):
    #active OSPF sur le routeur.
    index_line = find_index(router, "no ip http secure-server\n")
    insert_cfg_line(router, index_line, f"ipv6 router ospf 1\n router-id {router_id}\n")
    for interface in as_topology["routers"][router].values():
        index_line = find_index(router, f"interface {interface}\n") + 4
        insert_cfg_line(router, index_line, " ipv6 ospf 1 area 0\n")
    if is_border_routers(router, as_topology):
        index_line = find_index(router, "ip forward-protocol nd\n") - 1
        insert_cfg_line(router, index_line, "router ospf 1\n")
        for AS_neighbor in as_topology["neighbor"]:
            index_line =  find_index(router, f" router-id {router_id}\n")
            for interface in as_topology["neighbor"][AS_neighbor][router].values():
                insert_cfg_line(router, index_line, f" passive-interface {interface}\n")
        

def activate_rip(router, as_topology):
    #active RIP sur le routeur.
    rip_process_name = "process"
    index_line = find_index(router, "no ip http secure-server\n")
    insert_cfg_line(router, index_line, f"ipv6 router rip {rip_process_name}\n redistribute connected\n")
    for interface in as_topology["routers"][router].values():
        index_line = find_index(router, f"interface {interface}\n") + 4
        insert_cfg_line(router, index_line, f" ipv6 rip {rip_process_name} enable\n")

def give_router_id(router):
        x = router[1:]
        return f"{x}.{x}.{x}.{x}"

def activate_bgp(routeur, as_topology):
    #active BGP sur le routeur.
    pass

def is_border_routers(router, as_topology): 
    for AS_neighbor in as_topology["neighbor"]:
        return True if router in as_topology["neighbor"][AS_neighbor].keys() else False
        

"""def eBGP_configure(topology):
    #configure pour chaque AS comme clé le routeur, et comme valeur les routeurs eBGP et les interfaces.
    for AS in topology:
        for as_neighbor in topology[AS]['neighbor']:
            eBGP_routers(AS, as_neighbor)

def eBGP_routers(AS, as_neighbor, topology):
    for router_AS in topology[AS]['neighbor'][as_neighbor]:
        for router_as_neighbor, interface_AS in topology[AS]['neighbor'][as_neighbor][router_AS].items():
            interface_AS_neighbor = topology[as_neighbor]['neighbor'][AS][router_as_neighbor][router_AS]
            print(router_AS, interface_AS, router_as_neighbor, interface_AS_neighbor)
"""


topology = read_json("intents.json")
main(topology)