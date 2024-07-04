from logic.server import server
from hw.packet import Payload_type, Command_type, Packet_type, packet_dist, packet
from sim.debugger import debugger

from typing import List
import numpy as np
import random

class server_join(server):
    def __init__(self, AppID: int):
        super().__init__(AppID)

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
        self.last_time_broadcast = self.get_time() - 1000*60*40
        self.last_connection_check = self.get_time()

    # get next free packet id
    # counting up until 255 then return to 0
    # should be enough to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    def handle_packet(self, rx_packet : packet_dist):
        # add to local storage
        self.pack_list.append(rx_packet)

        # handle packet
        if(self.check_multiple_packet(rx_packet)):

            self.debugger.log("received at Server (%i): %s" % (self.appID, str(rx_packet)), 3)

            if(rx_packet.payload_type is Payload_type.JOIN):
                self.debugger.log("receiving join request from node with ID: %i with RSSI:%i" % (rx_packet.origin, rx_packet.rssi), 1)
                if(not rx_packet.origin in self.nodes_id):
                    self.num_connected_nodes += 1
                    self.first_connection[self.num_connected_nodes-1] = self.get_time()
                    # self.last_connection[self.num_connected_nodes-1] = self.node.get_time()
                    self.nodes_interval[self.num_connected_nodes-1] = rx_packet.payload[2]
                    self.nodes_id.append(rx_packet.origin)
                
                for gw in self.gateways:
                    # queue the packet to avoid bounces at the first node in the chain
                    gw.handle_server_request(
                        packet_dist(
                            self.appID,
                            gw.node_id,
                            rx_packet.origin,
                            10,
                            self.get_packet_id(),                   
                            0,
                            False,
                            Payload_type.ACK,
                            1
                        ),
                        random.randint(500, 2000)
                    )

            elif(rx_packet.payload_type is Payload_type.DATA):
                # update link quality statistics
                idx = self.nodes_id.index(rx_packet.origin)
                self.num_packets_received[idx] += 1
                self.num_packets_received_interval[idx] += 1
                self.last_connection[idx] = self.get_time()

                # store packet in DB
                self.store_packet(rx_packet)

    def update(self):
        if(self.get_time() == 1609459200000 + 10*60*60*1000 + 300000):
            self.debugger.log("Sending DELAY_INTERVAL request to node 3", 2)
            for gw in self.gateways:
                gw.handle_server_request(
                    packet_dist(
                        self.appID,
                        gw.node_id,
                        3,
                        10,
                        self.get_packet_id(),                   
                        0,
                        False,
                        Payload_type.COMMAND,
                        [Command_type.DELAY_INTERVAL, 2424]
                    )
                )
            
        # broadcast time sync packet to all nodes every hour
        if(self.get_time() - self.last_time_broadcast > self.time_broadcast):
            self.last_time_broadcast = self.get_time()
            self.debugger.log("Sending TIME_SYNC", 1)

            for gw in self.gateways:
                gw.handle_server_request(
                    packet_dist(
                        self.appID,
                        gw.node_id,
                        3,
                        10,
                        self.get_packet_id(),                   
                        0,
                        False,
                        Payload_type.TIME_SYNC,
                        self.get_time()
                    )
                )
        
        # check status of nodes
        if(self.get_time() - self.last_connection_check > self.interval_connection_check):
            self.last_connection_check = self.get_time()
            self.debugger.log("Checking node status", 1)
            for n in range(0, self.num_connected_nodes):
                # check if node was connected for full connection check interval
                if(self.first_connection[n] < self.get_time() - self.interval_connection_check):

                    # calc rough estimate of number of packets the node should have sent
                    pkg_sent = int( self.interval_connection_check / self.nodes_interval[n] ) 

                    # node is successfully connected
                    # received too few packets from node
                    # timing problems
                    # delay next sending interval of node
                    if(self.num_packets_received[n] > 0 and self.num_packets_received_interval[n] < pkg_sent * 0.8):
                        
                        self.debugger.log("Did not receive enough packets from node with ID: %i" % self.nodes_id[n] ,1)
                        for gw in self.gateways:
                            gw.handle_server_request(
                                packet_dist(
                                    self.appID,
                                    gw.node_id,
                                    3,
                                    10,
                                    self.get_packet_id(),                   
                                    0,
                                    False,
                                    Payload_type.COMMAND,
                                    [Command_type.DELAY_INTERVAL, 2424],
                                ),
                                random.randint(500, 2000) + n*15000
                            )

                    self.num_packets_received_interval[n] = 0
                    
                else:
                    self.debugger.log("node with ID: %s not connected for full interval" % str(self.nodes_id[n]).rjust(3), 1)

            # reset interval counter
            self.num_packets_received_interval = np.zeros((100))

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
            # print(self.last_packet_origins)
            # print("removing %i" % (remove[i]-i))
            self.last_packet_relay.pop(remove[i]-i)
            self.last_packet_origins.pop(remove[i]-i)
            self.last_packet_pid.pop(remove[i]-i)
            # print(self.last_packet_origins)
            self.debugger.log("Server (%i): not handling packet %s from node %i because it was received multiple times" % (self.appID, str(rx_packet.payload_type)[13:], rx_packet.origin), 3)

        if(num_blocks > 0):
            return False
        else:
            self.last_packet_relay.append(self.get_time())
            self.last_packet_origins.append(rx_packet.origin)
            self.last_packet_pid.append(rx_packet.packet_id)
            return True
        
    def store_packet(self, rx_packet : packet_dist):
        self.local_db.append(rx_packet)
        self.local_db_rx_time.append(self.get_time())