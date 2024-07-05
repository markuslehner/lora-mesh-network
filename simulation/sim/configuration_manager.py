from sim.event import event
from hw.node import node
from logic.logic_node_passive import logic_node_passive
from logic.server import server

from typing import List, Tuple
import pickle

"""
SETUP PARAMETERS
"""

# simulation time in ms
runtime : int = 1000200
# time for world in ms
world_time : int = 1609459200000 + 10*60*60*1000

# run in new thread in background
# only output to txt file
background : bool = False

additionalInfo : bool = True
# 0 - Off
# 1 - light
# 2 - mid
# 3 - heavy
# 4 - all
debug : int = 2   

# plot visualization of map
visualize : bool = False

# use same offset for all runs
use_same_offset : bool = False

# if None, LoRa range chart is used
tx_min : int = None
tx_max : int = None

# transmission model
tx_error_rate : float = None
tx_decay : float = None

# node list
nodes : List[node] = []
# list for blocks
# tuples specifying the indices of the blocking nodes in the 'nodes' list
blocks : List[Tuple[int,int]] = []
# list for events
event_list : List[event] = []
# server list
servers : List[server] = []

def register_event(e : event):
    global event_list
    event_list.append(e)

def register_node(n : node):
    global nodes
    nodes.append(n)

def register_server(s : server):
    global servers
    servers.append(s)

def register_block(a : int, b : int, uni_directional : bool = False):
    global blocks
    blocks.append((a,b))
    if(not uni_directional):
        blocks.append((b,a))

def set_tx_params(mint, maxt, er, dc):
    global tx_decay, tx_error_rate, tx_max, tx_min
    tx_min = mint
    tx_max = maxt
    tx_error_rate = er
    tx_decay = dc

def set_runtime(rt):
    global runtime
    runtime = rt

def write_configuration(cname : str):

    if(not use_same_offset):
        for n in nodes:
            if(type(n.logic) is logic_node_passive):
                n.logic.start_time_offset = None

    config = {
        "nodes" : {},
        "blocks": {},
        "config": {},
        "world" : {},
        "events": {},
        "servers" : {}
    }

    for i in range(0, len(nodes)):
        config.get("nodes").update({ ("%i" % i) : nodes[i].to_dict()})

    for i in range(0, len(servers)):
        config.get("servers").update({ ("%i" % i) : servers[i].to_dict()})

    config.update({ "blocks" : blocks})

    config.update({ "config" : {
        "world_time"                :   world_time,
        "runtime"                   :   runtime,
        "use_same_offset"           :   use_same_offset,
        "additionalInfo"            :   additionalInfo,
        "debug"                     :   debug,
        "visualize"                 :   visualize,
        "background"                :   background,
        "num_nodes"                 :   len(nodes),
        "num_servers"               :   len(servers)
    }})

    config.update({ "world" : {
        "tx_min"        : tx_min,
        "tx_max"        : tx_max,
        "tx_error_rate" : tx_error_rate,
        "tx_decay"      : tx_decay
    }})

    config.update({ "events" : event_list})

    with open("Simulation/config/%s.pkl" % cname, "wb") as f:
        pickle.dump(config, f)