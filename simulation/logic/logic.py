from hw.node import node
from logic.packet_handler import packet_handler
from sim.debugger import debugger

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

    def __init__(self, appID : int = 0, node_id : int = 0, handler : packet_handler=None):
        super().__init__()
        self.chapter = 0
        self.appID = appID
        self.node_id = node_id

        self.node : node = None
        self.debugger : debugger = None
        self.packetHandler : packet_handler = handler
        
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

    def __str__(self) -> str:
        return "%s     with handler: %s" % (str(type(self)).split(".")[-1][:-2].rjust(25), str(type(self.packetHandler)).split(".")[-1][:-2].rjust(20) )