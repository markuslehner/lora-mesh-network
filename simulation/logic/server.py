# TODO create class that handles the data and the command_center part of the network.
from hw.packet import lora_packet, Payload_type
from logic.logic_central import logic_central

from typing import List

class server(object):
    def __init__(self, AppID):
        self.AppID = AppID
        self.connected_nodes : List[int] = []
        self.gateways : List[logic_central] = []    
        self.registered_nodes : dict = {}

    def register_node(self, node):
        self.registered_nodes[node.node_id] = node

    def connect_node(self, node):
        self.connected_nodes.append(node)

    def handle_packet(self, packet : lora_packet):
        pass #TODO
