import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

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
    # Essaye de lire et extraire la topologie d'un json, sinon quitte le programme avec un message d'erreur
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
    with ThreadPoolExecutor() as executor:
        futures = []
        subnet_dict = give_subnet_number(topology)
        subnet_interconnexion_dict = give_subnet_interconnexion(topology, subnet_dict)
        for AS in topology:
            for router in topology[AS]['routers']:
                future = executor.submit(process_router, router, AS, subnet_dict[AS], subnet_interconnexion_dict[AS], topology)
                futures.append(future)

        for future in futures:
            future.result()


def process_router(router, AS, subnet_dict, subnet_interconnexion_dict, topology):
    create_base_cfg(router, base_config)
    create_loopback_interface(router, topology[AS])
    create_router_interfaces(router, AS, topology[AS], subnet_dict)
    activate_protocols(router, AS, topology[AS], subnet_interconnexion_dict,subnet_dict)


def insert_cfg_line(router, index_line, data):
    # insert une information 'data' à la ligne 'line'.
    with open(f'i{router[1:]}_startup-config.cfg', 'r') as file:
        lines = file.readlines()
        lines.insert(index_line, data)
    with open(f'i{router[1:]}_startup-config.cfg', 'w') as file:
        file.writelines(lines)


def create_base_cfg(router, base_config):
    # créer pour un routeur, son fichier cfg de base à partir d'une liste 'base config', et insert l'hostname.
    with open(f'i{router[1:]}_startup-config.cfg', 'w') as file:
        for entry in base_config:
            file.write(entry + '\n')
    insert_cfg_line(router, 3, f"hostname {router}\n")


def find_index(router, line):
    # Trouve l'indice correcte pour inserer une nouvelle ligne juste après la ligne 'line'.
    index_line = 1
    with open(f'i{router[1:]}_startup-config.cfg', 'r') as file:
        lines = file.readline()
        while lines != line:
            lines = file.readline()
            index_line += 1
    return index_line


def create_router_interfaces(router, AS, as_topology, subnet_dict):
    # insert dans le cfg du routeur toutes les ses interfaces et leurs ipv6 correspondantes.
    index_line = find_index(router, line="ip tcp synwait-time 5\n")

    for neighbor in as_topology['routers'][router].keys():
        if router[1:] < neighbor[1:]:
            subnet_index = subnet_dict[(router, neighbor)]
            router_index = 1
        else:
            subnet_index = subnet_dict[(neighbor, router)]
            router_index = 2

        insert_cfg_line(router, index_line,
                        f"interface {as_topology['routers'][router][neighbor]}\n no ip address\n negotiation auto\n ipv6 address {as_topology['address']}{subnet_index}::{router_index}{as_topology['subnet_mask']}\n ipv6 enable\n")
        index_line += 5


def give_subnet_number(as_topology):  # Crée le tableau des subnets pour tout le json
    subnet_dict = dict()
    for AS in as_topology:
        subnet_dict[AS] = dict()
        subnet_number = 1
        for router in as_topology[AS]['routers']:
            for neighbor in as_topology[AS]['routers'][router]:
                if router[1:] < neighbor[1:]:
                    subnet_dict[AS][(router, neighbor)] = subnet_number
                    subnet_number += 1
    return subnet_dict

def last_entries_subnet(subnet_dict):
    last_entry = dict()
    for AS in subnet_dict:
        last_entry[AS] = list(subnet_dict[AS].values())[-1]
    return last_entry
def give_subnet_interconnexion(as_topology, subnet_dict):  # Crée le tableau des subnets des interconnexion entre AS pour tout le json
    subnet_interconnexion_dict = dict()
    last_entries = last_entries_subnet(subnet_dict)
    for AS in as_topology:
        subnet_interconnexion_dict[AS] = dict()

    for AS in as_topology:
        for AS_neighbor in as_topology[AS]['neighbor']:
            for router1 in as_topology[AS]['neighbor'][AS_neighbor]:
                for router2 in as_topology[AS]['neighbor'][AS_neighbor][router1]:
                    if (router1, router2) not in subnet_interconnexion_dict[AS].keys() and (router2, router1) not in subnet_interconnexion_dict[AS].keys():
                        if AS < AS_neighbor:
                            subnet_interconnexion_dict[AS][(router1, router2)] = str(int(AS[3:])) + str((last_entries[AS] + 1)) + "::1"
                            subnet_interconnexion_dict[AS_neighbor][(router2, router1)] = str(int(AS[3:])) + str((last_entries[AS] + 1)) + "::2"
                        else:
                            subnet_interconnexion_dict[AS][(router1, router2)] = str(int(AS_neighbor[3:])) + str((last_entries[AS] + 1)) + "::1"
                            subnet_interconnexion_dict[AS_neighbor][(router2, router1)] = str(int(AS_neighbor[3:])) + str((last_entries[AS] + 1)) + "::2"
                        last_entries[AS] += 1
    return subnet_interconnexion_dict


def is_rip(as_topology):
    # retourne True si RIP est à activer, False sinon.
    return True if as_topology["protocol"] == "RIP" else False


def is_ospf(as_topology):
    # retourne True si RIP est à activer, False sinon
    return True if as_topology["protocol"] == "OSPF" else False


def activate_protocols(router, AS, as_topology, subnet_interconnexion_dict,subnet_dict):
    # active tous les protocols d'un routeur.
    router_id = give_router_id(router)
    if is_ospf(as_topology):
        activate_ospf(router, as_topology, router_id)
    elif is_rip(as_topology):
        activate_rip(router, as_topology)
    activate_bgp(router, AS, as_topology, subnet_interconnexion_dict,subnet_dict)


def activate_ospf(router, as_topology, router_id):
    # active OSPF sur le routeur.
    index_line = find_index(router, "no ip http secure-server\n")
    insert_cfg_line(router, index_line, f"ipv6 router ospf 1\n router-id {router_id}\n")
    for interface in as_topology["routers"][router].values():
        index_line = find_index(router, f"interface {interface}\n") + 4
        insert_cfg_line(router, index_line, " ipv6 ospf 1 area 0\n")

    if is_border_routers(router, as_topology):

        index_line = find_index(router, "ip forward-protocol nd\n") - 1
        insert_cfg_line(router, index_line, "router ospf 1\n")
        index_line = find_index(router, f" router-id {router_id}\n")
        for AS_neighbor in as_topology["neighbor"]:
            if router in as_topology["neighbor"][AS_neighbor].keys():
                for interface in as_topology["neighbor"][AS_neighbor][router].values():
                    insert_cfg_line(router, index_line, f" passive-interface {interface}\n")
                    

def activate_rip(router, as_topology):
    # active RIP sur le routeur.
    rip_process_name = "process"
    index_line = find_index(router, "no ip http secure-server\n")
    insert_cfg_line(router, index_line, f"ipv6 router rip {rip_process_name}\n redistribute connected\n")
    for interface in as_topology["routers"][router].values():
        index_line = find_index(router, f"interface {interface}\n") + 4
        insert_cfg_line(router, index_line, f" ipv6 rip {rip_process_name} enable\n")


def give_router_id(router):
    x = router[1:]
    return f"{x}.{x}.{x}.{x}"


def get_subnet_interconnexion(subnet_interconnexion_dict, routeur1, routeur2):
    return subnet_interconnexion_dict[(routeur1, routeur2)] or subnet_interconnexion_dict[(routeur2, routeur1)]


def activate_bgp(routeur, AS, as_topology, subnet_interconnexion_dict, subnet_dict):
    
    index_line = find_index(routeur, "ip forward-protocol nd\n") - 1
    if is_border_routers(routeur, as_topology):

        for AS_neighbor in as_topology["neighbor"]:
            for neighborRouter in as_topology["neighbor"][AS_neighbor]:
                if neighborRouter == routeur:
                    for neighborRouter2 in as_topology["neighbor"][AS_neighbor][neighborRouter]:
                        insert_cfg_line(routeur, index_line,
                                        f"interface {as_topology['neighbor'][AS_neighbor][neighborRouter][neighborRouter2]}\n no ip address\n negotiation auto\n ipv6 address {as_topology['address'][:-1]}{get_subnet_interconnexion(subnet_interconnexion_dict, routeur, neighborRouter2)}{as_topology['subnet_mask']}\n ipv6 enable\n")
                        index_line += 5
                        if is_ospf(as_topology):
                            insert_cfg_line(routeur, index_line," ipv6 ospf 1 area 0\n")
                            index_line +=1
                                            
    insert_cfg_line(routeur, index_line,
                    f"router bgp 10{AS[3:]}\n bgp router-id {give_router_id(routeur)}\n bgp log-neighbor-changes\n no bgp default ipv4-unicast\n")
    index_line += 4
    #neighbor autre as
    for AS_neighbor in as_topology["neighbor"]:
        if is_border_routers(routeur, as_topology):
           
            for subnet in subnet_interconnexion_dict:
                if subnet[0] == routeur:
                    if int(AS[3:]) < int(AS_neighbor[3:]):
                        network_tail = subnet_interconnexion_dict[subnet][:-1]+"2"
                        
                    else:
                        network_tail = subnet_interconnexion_dict[subnet][:-1]+"1"
                        

            insert_cfg_line(routeur, index_line, f" neighbor {as_topology['address'][:-1]}{network_tail} remote-as 10{AS_neighbor[3:]}\n")
            index_line +=1

    neighborConf = ""
    index_sum = 0
    for router in as_topology["routers"]:
        if router != routeur:
            neighborConf += f" neighbor 2001::{router[1:]} remote-as 10{AS[3:]}\n neighbor 2001::{router[1:]} update-source Loopback0\n"
            index_sum += 2
    insert_cfg_line(routeur, index_line, neighborConf)
    index_line += index_sum
    insert_cfg_line(routeur, index_line, f" address-family ipv4\n exit-address-family\n address-family ipv6\n")
    index_line += 3
    neighborConf = ""
    index_sum = 0

    for router in as_topology["routers"]:
        if router != routeur:
            neighborConf += f"  neighbor 2001::{router[1:]} activate\n"
            index_sum += 1
    if is_border_routers(routeur, as_topology):
        insert_cfg_line(routeur, index_line, f"  neighbor {as_topology['address'][:-1]}{network_tail} activate\n")
        index_line +=1

    insert_cfg_line(routeur, index_line, neighborConf)
    index_line += index_sum
    if is_border_routers(routeur, as_topology):
        
        create_networks(as_topology,routeur, subnet_dict, index_line)
        index_line +=1
    insert_cfg_line(routeur, index_line, " exit-address-family\n")


def is_border_routers(router, as_topology):
    state = False
    for AS_neighbor in as_topology["neighbor"]:
        if router in as_topology["neighbor"][AS_neighbor].keys():
            state = True
    return state

def create_networks(as_topology, router, subnet_dict, index_line):
    
    for AS_neighbor in as_topology["neighbor"]:        
        for AS in as_topology["pingable"]:
            if AS == AS_neighbor:
                network = as_topology["pingable"][AS]
                insert_cfg_line(router, index_line, f"  network {as_topology['address']}{subnet_dict[network[0][0], network[0][1]]}::{as_topology['subnet_mask']}\n" )
                
                    

def create_loopback_interface(router, as_topology):
    index_line = find_index(router, line="ip tcp synwait-time 5\n")
    insert_cfg_line(router, index_line, f"interface Loopback0\n no ip address\n ipv6 address 2001::{router[1:]}/128\n")
    index_line += 3
    if is_ospf(as_topology):
        insert_cfg_line(router, index_line, " ipv6 ospf 1 area 0\n")


if __name__ == "__main__":
    start = time.time()
    topology = read_json("network_intent.json")
    main(topology)
    end = time.time()
    print(end - start)
