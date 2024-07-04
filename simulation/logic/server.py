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

        # interval when to broadcast the timestamp
        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 0

        # list of all packets received by this nodeö
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

        self.num_connected_nodes = 0
        # time when node registered
        self.first_connection = np.zeros((100))
        # time since last packet received
        self.last_connection = np.zeros((100))
        # sending interval for the nodes in ms
        self.nodes_interval = np.zeros((100))
        # number of packets in total check
        self.num_packets_received = np.zeros((100))
        # number of packets since last connection check
        self.num_packets_received_interval = np.zeros((100))
        # interval when to check for inactivity of nodes
        self.last_connection_check = 0
        self.interval_connection_check = 1000*60*30
        # id of nodes
        self.nodes_id = []

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