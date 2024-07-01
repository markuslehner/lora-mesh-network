from sim.destroyed_packet import destroyed_packet, Destruction_type, Forward_type
from logic.packet_handler import packet_handler
from hw.packet import packet, Payload_type, Command_type
from hw.packet_flooding import packet_flooding
import random

class handler_flooding_pid(packet_handler):

    def __init__(self) -> None:
        super().__init__()
        # origin id of the relayed packet
        self.last_packet_origins = []
        # time a packet from this origin was last transmitted
        self.last_packet_relay = []
        # packet id of the packet
        self.last_packet_pid = []
        # time to wait until a packet from the same origin is relayed again
        self.relay_block_time = 15000  # old way = 0
        # time span out of which the random sending delay is taken
        self.relay_time = 5000
        # how often one single packet can be relayed
        self.relay_cnt = 1

    """
    Handles a received packet that is not intended for this node
    """
    def handle_packet(self, packet) -> packet:
        if(hasattr(self.node.logic, "connected")):
            if(self.node.logic.connected):
                self.relay_packet(packet)
        else:
            self.relay_packet(packet)


    """
    decide if packet needs to be re-transmittied
    prepare packet for further transport
    """
    def relay_packet(self, rx_packet : packet_flooding) -> None:
        # print("reached handler at node %s" % self.node.name)

        # print(packet.last_node)
        # print(packet.max_hops)

        fwd_reason = None
        largest_blocking_time = 0

        if(hasattr(self.node.logic, "connected") and rx_packet.num_hops == rx_packet.max_hops):
            # not connected, no forwarding
            fwd_reason = Forward_type.CONNECTED
        elif(rx_packet.num_hops == rx_packet.max_hops):
            #print("flood limit reached")
            fwd_reason = Forward_type.FLOOD_LIMIT
        elif(rx_packet.origin == self.node.id):
            # print("return to sender")
            fwd_reason = Forward_type.RETURN_TO_SENDER
        else:
            num_blocks, largest_blocking_time = self.get_num_received(rx_packet)

            # if packet was relayed more than twice in the last self.relay_block_time ms
            # don't forward it
            if(num_blocks > self.relay_cnt-1):
                self.node.debugger.log("Node %s: not forwarding packet [%s] from origin %s because of relay_block_time" % (self.node.name, rx_packet, rx_packet.origin), 4)
                fwd_reason = Forward_type.RELAY_BLOCK
            else:
                # update packet params
                rx_packet.add_hop(self.node)
                self.last_packet_origins.append(rx_packet.origin)
                self.last_packet_relay.append(self.node.get_time())
                self.last_packet_pid.append(rx_packet.packet_id)
                # send it
                self.node.debugger.log("Node %s: forwarding packet [%s] from origin %s" % (self.node.name, rx_packet, rx_packet.origin), 4)
                self.node.debugger.log("num_blocks: %i" % (num_blocks), 4)
                self.node.logic.queue_packet(rx_packet, random.randint(0, self.relay_time))

        if(not fwd_reason is None):
            self.node.debugger.add_destroyed_packet(destroyed_packet(
                    rx_packet,
                    rx_packet.sender,
                    self.node.id,
                    Destruction_type.FORWARD,
                    fwd_reason=fwd_reason,
                    largest_relay=largest_blocking_time,
                    relay_block=self.relay_block_time
                ))
            
    def get_num_received(self, rx_packet : packet_flooding) -> int:
        #check if forwarded packet from this origin in the last time
        remove = []
        largest_blocking_time = 0
        num_blocks = 0

        self.node.debugger.log("[%i, %i] %s %s" % (rx_packet.origin, rx_packet.packet_id, self.last_packet_origins, self.last_packet_pid), 5)

        for i in range(len(self.last_packet_origins)):
            # self.node.debugger.log("origin: %i/%i PID %i/%i" % (self.last_packet_origins[i], rx_packet.origin, self.last_packet_pid[i], rx_packet.packet_id), 5)
            if(rx_packet.payload_type != Payload_type.ROUTE and self.last_packet_origins[i] == rx_packet.origin and self.last_packet_pid[i] == rx_packet.packet_id):
                # get the time since entry in relay block list
                blocking_time = self.node.get_time() - self.last_packet_relay[i]
                # check if time is smaller than relay block --> is blocking
                if(blocking_time < self.relay_block_time):
                    num_blocks += 1
                    # keep track of oldest entry in relay_block_list for debugging
                    if(largest_blocking_time < blocking_time):
                        largest_blocking_time = blocking_time
                else:
                    remove.append(i)
            else:
                if(self.node.get_time() - self.last_packet_relay[i] > self.relay_block_time):
                    remove.append(i)
        
        for i in range(len(remove)):
            # print(self.last_packet_origins)
            # print("removing %i" % (remove[i]-i))
            self.last_packet_relay.pop(remove[i]-i)
            self.last_packet_origins.pop(remove[i]-i)
            self.last_packet_pid.pop(remove[i] - i)
            # print(self.last_packet_origins)
            self.node.debugger.log("Node %s: removed entry from block list, %i remaining" % (self.node.name, len(self.last_packet_relay)), 5)
       
        return num_blocks, largest_blocking_time
       
    def update_time(self, new_time):
        for i in range(len(self.last_packet_relay)):
            self.last_packet_relay[i] += new_time - self.node.get_time()
