from sim.debugger import debugger
from hw.packet import packet
import numpy as np

from typing import List

class server(object):
    def __init__(self, AppID : int):
        self.appID : int = AppID
        self.connected_nodes : List[int] = []
        self.gateways = [] 
        self.debugger : debugger = None

        # list of all packets received by this nodeö
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []
        
        '''NETWORK PARAMS'''
        # number of connected nodes
        self.num_connected_nodes = 0
        # time when node registered
        self.first_connection = np.zeros((100))
        # time since last packet received
        self.last_connection = np.zeros((100))
        # number of packets in total check
        self.num_packets_received = np.zeros((100))
        # number of packets since last connection check
        self.num_packets_received_interval = np.zeros((100))
        # id of nodes
        self.node_ids = []

    def set_debugger(self, debugger : debugger):
        self.debugger = debugger

    def register_gateway(self, gw):
        self.gateways.append(gw)

    def connect_node(self, node):
        self.connected_nodes.append(node)

    def register_in_world(self, world):
        self.world = world

    def get_time(self):
        return self.world.get_time()

    def handle_packet(self, packet):
        pass #TODO

    def update(self):
        pass #TODO

    def setup(self):
        pass #TODO

    def to_dict(self):
        return {
            "type"  : type(self),
            "appID" : self.appID,
        }

    def __str__(self):
        return "Server %i" % self.appID
    
    @classmethod
    def from_dict(cls, d : dict):
        return cls(d["appID"])