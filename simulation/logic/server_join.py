from logic.server import server
from hw.packet import Payload_type, packet_dist

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

        '''NETWORK PARAMS'''
        # distance that the node was assigned
        self.node_distances = []
        # node at which a multihop node first contacted the network
        self.node_of_first_contact = []

        '''JOIN PARAMS'''
        # time to wait for join requests to decide which node to add first
        # should be double the join repeat interval
        self.last_join_check = 0
        self.interval_join_check = 1000*60
        # number of received join requests in last interval
        self.num_received_join_requests = 0
        # all received join requests, store the id of node here
        self.received_join_requests = np.zeros((100))
        # RSSI of received requests
        self.received_join_requests_rssi = np.zeros((100))
        # node where a node connection over multi hop first got into contact with the network
        # distance of the first neighbour can be retreived from self.nodes_distances 
        # if it is greater than 0, the rssi to be stored is the RSSI the first neighbout received that packet with
        self.received_join_requests_first_node = np.zeros((100))
        

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

            self.debugger.log("received at Server (%i): %s" % (self.appID, str(rx_packet)), 3)

            if(rx_packet.payload_type is Payload_type.JOIN):
                self.debugger.log("receiving join request from node with ID: %i with RSSI:%i %s" % (rx_packet.origin, rx_packet.rssi, str(rx_packet.payload)), 3)
                self.received_join_requests[self.num_received_join_requests] = rx_packet.origin

                # if packet has not been relayed
                # payload of packet (=RSSI of first relay) is 0
                if(rx_packet.payload[0] == 0):
                    self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.rssi
                    self.received_join_requests_first_node[self.num_received_join_requests] = 0
                else:
                    self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.payload[0]
                    self.received_join_requests_first_node[self.num_received_join_requests] = rx_packet.payload[1]

                self.num_received_join_requests += 1 

            elif(rx_packet.payload_type is Payload_type.DATA):
                # update link quality statistics
                idx = self.node_ids.index(rx_packet.origin)
                self.num_packets_received[idx] += 1
                self.num_packets_received_interval[idx] += 1
                self.last_connection[idx] = self.get_time()

                # store packet in DB
                self.store_packet(rx_packet)

    def update(self):
        ''' 
        JOIN REQUESTS
        handle all join requests that were received in the last interval
        '''
        if(self.get_time() - self.last_join_check > self.interval_join_check):
            self.debugger.log("  JOIN CHECK:", 3)
            self.debugger.log("    received %i join requests" % self.num_received_join_requests, 3)

            # if the nodes started sending the JOIN requests are scheduled to avoid
            # the sending interval
            # when the nodes are sleeping they are only handled once every interval

            self.last_join_check += self.interval_join_check

            node_to_join = None
            node_to_join_dist = 1
            node_to_join_first_node = 0
            
            '''
            decide which nodes should be allowed to join next

            always add the node with the lowest RSSI
            only add one node at a time
            
            get distance of node (B) that received the JOIN request
            assign node (A) the distance of node (B) + 1
            '''
            # received a JOIN request directly at central
            if(self.num_received_join_requests > 0):

                idx = np.argmax(self.received_join_requests_rssi[:self.num_received_join_requests])
                node_to_join = self.received_join_requests[idx]
                node_to_join_first_node = self.received_join_requests_first_node[idx]
                node_to_join_dist = 1

                if(node_to_join in self.node_ids):
                    node_to_join_dist = self.node_distances[self.node_ids.index(int(node_to_join))]
                elif(not node_to_join_first_node == 0):
                    node_to_join_dist = self.node_distances[self.node_ids.index(int(node_to_join_first_node))] + 1

                # update connected node parameters
                # and
                # send the join requests
                if(not node_to_join in self.node_ids):
                    self.num_connected_nodes += 1
                    self.first_connection[self.num_connected_nodes-1] = self.get_time()
                    self.node_ids.append(int(node_to_join))
                    self.node_distances.append(node_to_join_dist)
                    self.node_of_first_contact.append(node_to_join_first_node)

                else:
                    self.debugger.log("    Node %i: rejoining" % node_to_join, 2)
                    idx = self.node_ids.index(node_to_join)

                self.debugger.log("    Server (%i): Sending JOIN_ACK to node %i for dist: %i" % (self.appID, node_to_join, node_to_join_dist), 2)
                for gw in self.gateways:
                    # queue the packet to avoid bounces at the first node in the chain
                    gw.handle_server_request(
                        packet_dist(
                            self.appID,
                            gw.node_id,
                            node_to_join,
                            10,
                            self.get_packet_id(),                   
                            0,
                            False,
                            Payload_type.ACK,
                            node_to_join_dist
                        ),
                        random.randint(500, 2000)
                    )

            # reset join info
            self.received_join_requests = np.zeros((100))
            self.received_join_requests_rssi = np.zeros((100))
            self.received_join_requests_first_node = np.zeros((100))
            self.num_received_join_requests = 0

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