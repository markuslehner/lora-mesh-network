import random
from logic.server import server
from hw.packet import LoRaWAN_type, packet_dist, lorawan_packet, Packet_type

from typing import List

class server_lorawan(server):
    def __init__(self, AppID: int, NwkKey : int):
        super().__init__(AppID)

        self.NwkKey : int = NwkKey
        self.encryption_keys : List[int] = []

        # packet id stuff
        self.next_packet_id = 0
        # origin id of the relayed packet
        self.last_packet_origins = []
        # time a packet from this origin was last transmitted
        self.last_packet_relay = []
        # packet id of the packet
        self.last_packet_pid = []
        # time to wait until a packet from the same origin is relayed again
        self.store_block_time = 10000  # old way = 0
        

    def setup(self):
        self.last_join_check = self.get_time()


    # get next free packet id
    # counting up until 255 then return to 0
    # should be enough to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    def handle_packet(self, rx_packet : packet_dist, gw_id : int):
        # add to local storage
        self.pack_list.append(rx_packet)

        # handle packet
        if(self.check_multiple_packet(rx_packet)):

            self.debugger.log("received at Server (%i): %s" % (self.appID, str(rx_packet)), 2)

            if(rx_packet.payload_type is LoRaWAN_type.JOIN_REQUEST):
                self.debugger.log("receiving join request from node with ID: %i with RSSI:%i %s" % (rx_packet.origin, rx_packet.rssi, str(rx_packet.payload)), 3)
                if rx_packet.payload[0] == self.NwkKey:
                    # update connected node parameters
                    # and   
                    # send the join requests
                    if(not rx_packet.origin in self.node_ids):
                        self.num_connected_nodes += 1
                        self.first_connection[self.num_connected_nodes-1] = self.get_time()
                        self.node_ids.append(int(rx_packet.origin))
                        self.encryption_keys.append(random.randint(0, 255))
                    else:
                        self.debugger.log("    Node %i: rejoining" % rx_packet.origin, 2)
                        self.encryption_keys[self.node_ids.index(rx_packet.origin)] = random.randint(0, 255)

                    for gw in self.gateways:
                        gw.handle_server_request(lorawan_packet(
                            self.appID,
                            gw.node_id,
                            rx_packet.origin,
                            LoRaWAN_type.JOIN_ACCEPT,
                            [self.encryption_keys[self.node_ids.index(rx_packet.origin)]],
                            packet_id= self.get_packet_id()
                        ), delay=350)
                        


            elif(rx_packet.payload_type is LoRaWAN_type.UNCONFIRMED_DATA_UP):
                # update link quality statistics
                idx = self.node_ids.index(rx_packet.origin)
                self.num_packets_received[idx] += 1
                self.num_packets_received_interval[idx] += 1
                self.last_connection[idx] = self.get_time()

                # store packet in DB
                self.store_packet(rx_packet)


    def update(self):
        pass

    # checks if this packet has already been received
    # returns handle packet? --> True / False
    def check_multiple_packet(self, rx_packet : packet_dist):

         #check if forwarded packet from this origin in the last time
        remove = []
        largest_blocking_time = 0
        num_blocks = 0

        for i in range(len(self.last_packet_origins)):
            if(self.last_packet_origins[i] == rx_packet.origin and self.last_packet_pid[i] == rx_packet.packet_id):

                # get the time since entry in relay block list
                blocking_time = self.get_time() - self.last_packet_relay[i]
                # check if time is smaller than relay block --> is blocking
                if(blocking_time < self.store_block_time):
                    num_blocks += 1
                    # keep track of oldest entry in relay_block_list for debugging
                    if(largest_blocking_time < blocking_time):
                        largest_blocking_time = blocking_time
                else:
                    remove.append(i)
            else:
                if(self.get_time() - self.last_packet_relay[i] > self.store_block_time):
                    remove.append(i)
        
        for i in range(len(remove)):
            self.last_packet_relay.pop(remove[i]-i)
            self.last_packet_origins.pop(remove[i]-i)
            self.last_packet_pid.pop(remove[i]-i)

        if(num_blocks > 0):
            self.debugger.log("Server (%i): not handling packet %s from node %i because it was received multiple times" % (self.appID, str(rx_packet.payload_type)[13:], rx_packet.origin), 3)
            return False
        else:
            self.last_packet_relay.append(self.get_time())
            self.last_packet_origins.append(rx_packet.origin)
            self.last_packet_pid.append(rx_packet.packet_id)
            return True
        
    def store_packet(self, rx_packet : packet_dist):
        self.local_db.append(rx_packet)
        self.local_db_rx_time.append(self.get_time())

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "NwkKey" : self.NwkKey
        })
        return d

    @classmethod
    def from_dict(cls, d : dict):
        return cls(
            d["appID"],
            d["NwkKey"])
    