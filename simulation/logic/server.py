from sim.debugger import debugger

from typing import List

class server(object):
    def __init__(self, AppID : int):
        self.appID : int = AppID
        self.connected_nodes : List[int] = []
        self.gateways = [] 
        self.debugger : debugger = None

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