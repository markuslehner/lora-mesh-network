from logic.packet_handler import packet_handler
from sim.destroyed_packet import destroyed_packet, Destruction_type, Forward_type
from hw.packet import Payload_type, Command_type, packet_flooding

import random

class handler_flooding_basic(packet_handler):

    def __init__(self) -> None:
        super().__init__()

        # time span out of which the random sending delay is taken
        self.relay_time = 2000

    """
    Handles a received packet that is not intended for this node
    """
    def handle_packet(self, packet : packet_flooding):
        
        if(packet.payload_type == Payload_type.COMMAND and packet.payload[0] == Command_type.REQUEST):
            self.node.debugger.log("%s: forwarding REQUEST target_distance:%i" % (self.node.name, packet.target_distance), 4)

        if(hasattr(self.node.logic, "connected")):
            if(self.node.logic.connected):
                self.relay_packet(packet)
        else:
            self.relay_packet(packet)

    """
    decide if packet needs to be re-transmittied
    prepare packet for further transport
    """
    def relay_packet(self, packet : packet_flooding):
        
        fwd_reason = None

        if(hasattr(self.node.logic, "connected") and not self.node.logic.connected):
            # not connected, no forwarding
            fwd_reason = Forward_type.CONNECTED
        elif(packet.num_hops == packet.max_hops):
            #print("flood limit reached")
            fwd_reason = Forward_type.FLOOD_LIMIT
        elif(packet.origin == self.node.logic.node_id):
            # print("return to sender")
            fwd_reason = Forward_type.RETURN_TO_SENDER
        else:
            packet.add_hop(self.node)
            # send it
            self.node.logic.queue_packet(packet, random.randint(0, self.relay_time))

        if(not fwd_reason is None):
            self.node.debugger.add_destroyed_packet(destroyed_packet(
                    packet,
                    packet.sender,
                    self.node.id,
                    Destruction_type.FORWARD,
                    fwd_reason=fwd_reason
                ))