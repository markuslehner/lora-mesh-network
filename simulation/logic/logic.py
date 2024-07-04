from hw.node import node
from sim.debugger import debugger
from logic.server import server
from hw.packet import packet, lora_packet
from hw.packet import Packet_type

from typing import List

"""
class representing the code that goes onto the MCU
"""
class logic(object):

    def __init__(self):
        super().__init__()
        self.chapter = 0
        self.node : node = None
        self.debugger : debugger = None

    def register(self, node : node) -> None:
        self.node = node

    def set_debugger(self, debugger : debugger) -> None:
        self.debugger = debugger

    def setup(self):
        return None

    """
    logic for the MCU of Sensor goes here
    with sleeping functionaility
    """
    def update_loop(self) -> None:
        pass
    
    def reset(self):
        self.debugger.log("Resetting logic %s" % self.name, 2)

    def to_dict(self) -> dict:
        return {
            "type"  : type(self)
        }

    @classmethod
    def from_dict(cls, d):
        return cls()

    def __str__(self) -> str:
        return str(type(self)).split(".")[-1][:-2].rjust(25)

"""
class representing the code framework for creating code to simulate a node
"""
class logic_node(logic):

    def __init__(self,  appID : int = 0, node_id : int = 0):
        super().__init__()
        self.chapter = 0
        self.appID = appID
        self.node_id = node_id

        self.node : node = None
        self.debugger : debugger = None
        
        # queue for packets to be sent later
        self.packet_queue = []
        self.packet_queue_timer = []

        # statistics
        self.send_cnt = 0

    def register(self, node : node) -> None:
        self.node = node

    def set_debugger(self, debugger : debugger) -> None:
        self.debugger = debugger

    def setup(self):
        pass

    """
    logic for the MCU of Sensor goes here
    with sleeping functionaility
    """
    def update_loop(self) -> None:

        # check packet queue
        if(len(self.packet_queue) > 0):
            #self.debugger.log("updating delayed packets %i" % len(self.packet_queue), 4)
            remove = []
            for i in range(0, len(self.packet_queue)):
                if(self.node.get_time() - self.packet_queue_timer[i] > 0):
                    self.debugger.log("Node %s: sending delayed packet" % self.node.name, 4)
                    remove.append(i)
                    self.node.get_transceiver().send(self.packet_queue[i])
                    
            for i in range(len(remove)):
                self.packet_queue_timer.pop(remove[i]- i)
                self.packet_queue.pop(remove[i]- i)

        return None

    def clear_packet_queue(self):
        self.packet_queue = []
        self.packet_queue_timer = []

    def queue_packet(self, packet, time):
        self.debugger.log("Node %s: queueing delayed packet for %i ms" % (self.node.name, time), 4)
        self.packet_queue.append(packet)
        self.packet_queue_timer.append(self.node.get_time() + time)
    
    # update all dependencies on the time
    # e.g. packet queue
    def update_time(self, new_time) -> None:

        for i in range(len(self.packet_queue)):
            self.packet_queue_timer[i] += new_time - self.node.get_time()

        # always last bacsue otherwise
        # node.time == new_time
        self.node.set_time(new_time)
        self.debugger.log("setting time @ node %s to %i (corect time is: %i)" % (self.node.name, self.node.get_time(), self.node.get_transceiver().world.get_time()), 1)

    def reset(self):
        self.debugger.log("Resetting logic %s" % self.name, 2)

    def to_dict(self) -> dict:
        return {
            "type"  : type(self),
            "appID" : self.appID,
            "node_id" : self.node_id
        }

    @classmethod
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id")
        )
        return instance
    

class logic_node_lora(logic_node):
    def __init__(self, appID : int = 0, node_id : int = 0, handler = None, spreading_factor : int = 7) -> None:
        super().__init__(appID, node_id)
        self.packetHandler = handler
        self.spreading_factor = spreading_factor

    def setup(self):
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_%i" % self.spreading_factor)
        self.node.get_transceiver().set_tx_power(14)

        if self.packetHandler is not None:
            self.packetHandler.register(self.node)

    def to_dict(self) -> dict:
        d =  super().to_dict()
        d.update({"spread" : self.spreading_factor})
        d.update({"packet_handler" : type(self.packetHandler)})
        return d
    
    @classmethod
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("packet_handler").from_dict(d),
            d.get("spread")
        )
        return instance

    def __str__(self) -> str:
        return "%s     with handler: %s" % (str(type(self)).split(".")[-1][:-2].rjust(25), str(type(self.packetHandler)).split(".")[-1][:-2].rjust(20) )
    

class logic_central(logic_node_lora):
    def __init__(self, appID : int, node_id : int, handler, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, handler, spreading_f)

        # list of all packets received by this node
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

    def update_loop(self): 
        super().update_loop()

        if(self.chapter == 0):

            if(self.node.get_transceiver().has_received()):
                # print(self.node.get_transceiver().rec_list)
                rx_packet = self.node.get_transceiver().get_received()
                self.receive(rx_packet)     
        else:
            self.node.wait(10)

    def receive(self, rx_packet : packet) -> None:
        pass
    
    def store_packet(self, rx_packet) -> None:
        self.pack_list.append(rx_packet)
        self.local_db.append(rx_packet)
        self.local_db_rx_time.append(self.node.get_time())


class logic_central_lora(logic_central):
    def __init__(self, appID, node_id : int, handler = None, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, handler, spreading_f)

    def receive(self, rx_packet: lora_packet) -> None:
        if rx_packet.packet_type == Packet_type.LORA:
            # check if its the same network
            if rx_packet.appID == self.appID:
                if rx_packet.target == self.node_id or rx_packet.target == 0:
                    self.store_packet(rx_packet)


class logic_gateway(logic_node_lora):

    def __init__(self, appID : int, node_id : int, handler, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, handler, spreading_f)

    def setup(self):
        super().setup()
        self.server : server = self.node.transceiver.world.get_server(self.appID)
        self.server.register_gateway(self)

    def handle_server_request(self, rx_packet : packet, delay : int = 0):
        self.debugger.log("Handling server request: %s" % str(rx_packet), 5)
        self.queue_packet(rx_packet, delay)

    def update_loop(self): 
        super().update_loop()