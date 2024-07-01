from logic.handler_flooding import handler_flooding
from hw.packet import Payload_type, Command_type, Packet_type, lora_packet, packet_flooding
from logic.logic_central import logic_central

import numpy as np
import datetime
import random

class logic_central_pid(logic_central):

    def __init__(self, appID=0, node_id=0, db=False, handler=handler_flooding()) -> None:
        super().__init__(appID, node_id, db, handler)

        # interval when to broadcast the timestamp
        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 0

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

        self.write_db = db

    def setup(self):

        super().setup()

        self.last_time_broadcast = self.node.get_time() - 1000*60*40
        self.last_connection_check = self.node.get_time()

    # get next free packet id
    # counting up until 255 then return to 0
    # should be enouh to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    def update_loop(self):

        super().update_loop()

        if(self.chapter == 0):

            if(self.node.get_transceiver().has_received()):
                # print(self.node.get_transceiver().rec_list)
                if(rx_packet.packet_type == Packet_type.LORA):
                    rx_packet : lora_packet = self.node.get_transceiver().get_received()
                    self.receive(rx_packet)

            if(self.node.get_time() == 1609459200000 + 10*60*60*1000 + 300000):
                self.debugger.log("Sending DELAY_INTERVAL request to node 3", 2)
                self.node.get_transceiver().send(
                    packet_flooding(
                        self.appID,
                        self.node_id,
                        3,
                        Payload_type.COMMAND,
                        [Command_type.DELAY_INTERVAL, 2424],
                        7,
                        packet_id=self.get_packet_id()
                    )
                )
            
            # broadcast time sync packet to all nodes every hour
            if(self.node.get_time() - self.last_time_broadcast > self.time_broadcast):
                self.last_time_broadcast = self.node.get_time()

                self.debugger.log("Sending TIME_SYNC", 1)

                self.node.get_transceiver().send(
                    packet_flooding(
                        self.appID,
                        self.node_id,
                        0,
                        Payload_type.TIME_SYNC,
                        self.node.get_time(),
                        5,
                        packet_id=self.get_packet_id()
                    )
                )
            
            # check status of nodes
            if(self.node.get_time() - self.last_connection_check > self.interval_connection_check):
                self.last_connection_check = self.node.get_time()
                self.debugger.log("Checking node status", 1)
                for n in range(0, self.num_connected_nodes):
                    # check if node was connected for full connection check interval
                    if(self.first_connection[n] < self.node.get_time() - self.interval_connection_check):

                        # calc rough estimate of number of packets the node should have sent
                        pkg_sent = int( self.interval_connection_check / self.nodes_interval[n] ) 

                        # node is successfully connected
                        # received too few packets from node
                        # timing problems
                        # delay next sending interval of node
                        if(self.num_packets_received[n] > 0 and self.num_packets_received_interval[n] < pkg_sent * 0.8):
                            
                            self.debugger.log("Did not receive enough packets from node with ID: %i" % self.nodes_id[n] ,1)
                            
                            self.queue_packet(
                                packet_flooding(
                                    self.appID,
                                    self.node_id,
                                    self.nodes_id[n],
                                    Payload_type.COMMAND,
                                    [Command_type.DELAY_INTERVAL, 2424],
                                    7,
                                    packet_id=self.get_packet_id()
                                ),
                                random.randint(500, 2000) + n*15000
                            )

                        self.num_packets_received_interval[n] = 0
                        
                    else:
                        self.debugger.log("node with ID: %s not connected for full interval" % str(self.nodes_id[n]).rjust(3), 1)

                # reset interval counter
                self.num_packets_received_interval = np.zeros((100))
       
        else:
            self.node.wait(10)

    def receive(self, rx_packet : packet_flooding) -> None:

        if(rx_packet.appID == self.appID):
            if(rx_packet.target == self.node_id or rx_packet.target == 0):
                
                # add to local storage
                self.pack_list.append(rx_packet)

                # handle packet
                if(self.check_multiple_packet(rx_packet)):

                    self.debugger.log("received at central: %s" % str(rx_packet), 4)

                    if(rx_packet.payload_type is Payload_type.JOIN):
                        self.debugger.log("receiving join request from node with ID: %i with RSSI:%i" % (rx_packet.origin, rx_packet.rssi), 1)
                        if(not rx_packet.origin in self.nodes_id):
                            self.num_connected_nodes += 1
                            self.first_connection[self.num_connected_nodes-1] = self.node.get_time()
                            # self.last_connection[self.num_connected_nodes-1] = self.node.get_time()
                            self.nodes_interval[self.num_connected_nodes-1] = rx_packet.payload
                            self.nodes_id.append(rx_packet.origin)
                        
                        # queue the packet to avoid bounces at the first node in the chain
                        self.queue_packet(
                            packet_flooding(
                                self.appID,
                                self.node_id,
                                rx_packet.origin,
                                Payload_type.ACK,
                                self.node.get_time(),
                                10,
                                packet_id=self.get_packet_id()
                            ),
                            random.randint(500, 2000)
                        )

                    elif(rx_packet.payload_type is Payload_type.DATA):
                        # update link quality statistics
                        idx = self.nodes_id.index(rx_packet.origin)
                        self.num_packets_received[idx] += 1
                        self.num_packets_received_interval[idx] += 1
                        self.last_connection[idx] = self.node.get_time()

                        # store packet in DB
                        self.store_packet(rx_packet)

        else:
            self.packetHandler.handle_packet(rx_packet)

    # checks if this packet has already been received
    # returns handle packet? --> True / False
    def check_multiple_packet(self, rx_packet):

         #check if forwarded packet from this origin in the last time
        remove = []
        largest_blocking_time = 0
        num_blocks = 0

        for i in range(len(self.last_packet_origins)):
            if(self.last_packet_origins[i] == rx_packet.origin and self.last_packet_pid[i] == rx_packet.packet_id):

                # get the time since entry in relay block list
                blocking_time = self.node.get_time() - self.last_packet_relay[i]
                # check if time is smaller than relay block --> is blocking
                if(blocking_time < self.store_block_time):
                    num_blocks += 1
                    # keep track of oldest entry in relay_block_list for debugging
                    if(largest_blocking_time < blocking_time):
                        largest_blocking_time = blocking_time
                else:
                    remove.append(i)
            else:
                if(self.node.get_time() - self.last_packet_relay[i] > self.store_block_time):
                    remove.append(i)
        
        for i in range(len(remove)):
            # print(self.last_packet_origins)
            # print("removing %i" % (remove[i]-i))
            self.last_packet_relay.pop(remove[i]-i)
            self.last_packet_origins.pop(remove[i]-i)
            self.last_packet_pid.pop(remove[i]-i)
            # print(self.last_packet_origins)
            self.node.debugger.log("Node %s: not handling packet %s from node %i because it was received multiple times" % (self.node.name, str(rx_packet.payload_type)[13:], rx_packet.origin), 3)

        if(num_blocks > 0):
            return False
        else:
            self.last_packet_relay.append(self.node.get_time())
            self.last_packet_origins.append(rx_packet.origin)
            self.last_packet_pid.append(rx_packet.packet_id)
            return True


    def store_packet(self, rx_packet):

        self.local_db.append(rx_packet)
        self.local_db_rx_time.append(self.node.get_time())

        if(self.write_db):
            # local debug
            """
            Create a new packet into the packets table
            :param conn:
            :param packet:
            :return: project id
            """
            sql = ''' INSERT INTO packets(sender,type,data,time_received)
                    VALUES(?,?,?,?) '''
            cur = self.conn.cursor()
            cur.execute(sql, (
                rx_packet.origin,
                str(rx_packet.payload_type)[13:],
                rx_packet.payload,
                datetime.datetime.fromtimestamp(int(self.node.get_time()/1000)).strftime("%H:%M:%S")
            ))
            self.conn.commit()

    def to_dict(self) -> dict:
        return {
            "type"  : type(self),
            "appID" : self.appID,
            "node_id" : self.node_id,
            "store" : self.write_db,
            "handler" : type(self.packetHandler)
        }

    @classmethod
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("store"),
            d.get("handler").from_dict(d)
        )
        return instance
