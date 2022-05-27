import numpy as np
import pickle
import sys
import os

if( os.path.basename(sys.argv[0]) == 'test_command_center.py' ):
    print("setting lora class")
    class Rak811(object):
        def __init__(self) -> None:
            super().__init__()
else:
    from rak811.rak811_v3 import Rak811, Rak811ResponseError
    from rak811.serial import Rak811TimeoutError

from lib.packet import packet, Payload_type, Command_type
from lib.packet_db import packet_db
from lib.logger import logger
from lib.command_center import command_center
from lib.command import command, request_command, nack_command, ack_command, ack_join_command, set_interval_command, resync_interval_command

from datetime import datetime

class packet_handler(object):

    def __init__(self, db_name: str, id: int, app_id: bytes, lora: Rak811, blocks : list, log : logger) -> None:
        super().__init__()

        # own params
        self.id = id
        self.app_id = app_id
        self.lora : Rak811 = lora
        self.artificial_blocks = blocks
        self.logger : logger = log

        # queue for packets to be sent later
        self.packet_queue : 'list[packet]' = [] 
        self.packet_queue_timer = []

        # if state was restored from pickle
        # needed to avoid receive check
        self.state_restored = False

        '''
        COMMANDS
        '''
        # command priority and timing
        self.command_center : command_center = command_center(self.app_id, self.id, self, self.logger)

        '''
        INTERVAL PARAMETERS
        '''
         # interval in which nodes should broadcast
        self.interval = 1000*60*5 #interval
        # time the next interval will start
        # calculate that is always starts on an even minute
        milliseconds_from_minute = self.get_time() % ( self.interval )
        self.next_interval_start = self.get_time() + self.interval - milliseconds_from_minute
        # time the last interval started
        self.last_interval_start = self.next_interval_start - self.interval
        self.logger.log("CREATING PACKET_HANDLER: Last interval start: %s" % (datetime.fromtimestamp(int(self.last_interval_start/1000)).strftime("%H:%M:%S")), 1)
        self.logger.log("CREATING PACKET_HANDLER: Next interval start: %s" % (datetime.fromtimestamp(int(self.next_interval_start/1000)).strftime("%H:%M:%S")), 1)
        # size of a sending_slot for one node
        self.interval_slot_width = int(1000*7.5)
        # time that the active interval time is extended to allow for other transmissions
        self.interval_active_extension = 1000*20

        '''JOIN PARAMS'''
        # time to wait for join requests to decide which node to add first
        # should be double the join repeat interval
        self.last_join_check = self.get_time()
        self.interval_join_check = 1000*40
        # number of received join requests in last interval
        self.num_received_join_requests = 0
        # all received join requests, store the id of node here
        self.received_join_requests = np.zeros((100))
        # RSSI of received requests
        self.received_join_requests_rssi = np.zeros((100))
        # node where a node connection over multi hop first got into contact with the network
        # distance of the first neighbour can be retreived from self.nodes_distances 
        # if it is greater than 0, the rssi to be stored is the RSSI the first neighbout received that packet with
        self.received_join_requests_first_node = np.ones((100))*self.id
        # new nodes to join
        self.new_nodes_to_join = False
        # ids of nodes that sent join in last interval
        self.nodes_joined_last_interval = []
        
        # number of consecutive join intervals without a new join request
        self.num_empty_join_intervals = 0
        # number of join intervals to switch to assign mode
        self.required_num_emtpy_join = 3

        '''INTERVAL SYNC PARAMS'''
        # nodes that accepted the interval
        # order is same as in self.node_ids
        # True if ACK received
        # False if not
        self.node_interval_ack = []
        # if SET_INTERVAL command was queued for this node
        self.node_interval_sent = []
        # interval broadcast timing
        self.interval_broadcast = 1000*80
        self.last_interval_broadcast = self.next_interval_start - self.interval_broadcast
        # first interval broadcast complete
        # and nodes started sending
        self.nodes_started_sending = False
        # rebroadcast interval to combat drift in sync with random wake-up jitter
        # number of successfull intervals after which to broadcast interval data
        self.interval_resync_after = 4
        # current number of successfull intervals
        self.interval_count = 0


        '''NETWORK PARAMS'''
        # if the network was successfully configured
        # if at least one DATA packet from all connected nodes was received
        self.all_nodes_sending = False
        # if the nodes are in sleeping mode
        # indicates at least one successfull start of the network
        self.successfully_started = False
        # if the network is running as configured
        self.network_running = False
        # nodes sleeping between intervals
        self.nodes_sleeping = False
        # number of connected nodes
        self.num_connected_nodes = 0
        # time when node registered
        self.first_connection = np.zeros((100))
        # time since last packet received
        self.last_connection = np.zeros((100))
        # number of packets in total check
        self.num_packets_received = np.zeros((100))
        # number of packets since last connection check
        self.num_packets_received_interval = np.zeros((100))
        # id of nodes
        self.node_ids = []
        # distance that the node was assigned
        self.node_distances = []
        # node at which a multihop node first contacted the network
        self.node_of_first_contact = []
        # current battery level of the nodes
        self.node_battery_level = []
        # sending status of the nodes
        self.node_sending_status = []
        # sleeping status of the nodes
        self.node_sleeping_status = []
        # wanted sleeping status of the nodes
        self.node_wanted_sleeping_status = []
        # received routes, used to create better network graph and allow fine tuning
        self.routes = []
        # pre assigned distances
        # self.assigned_distances : dict = {}
        self.assigned_distances : dict = {
            "1" : 1,
            "2" : 2,
            "3" : 3,
            "4" : 4,
            "5" : 5,
            "6" : 5,
        }
        # white-list
        self.white_list = [1, 2, 3, 4, 5, 6]

        '''DUPLICATE DETECTION'''
        # origin id of the relayed packet
        self.last_packet_origins = []
        # time a packet from this origin was last transmitted
        self.last_packet_relay = []
        # packet id of the packet
        self.last_packet_pid = []
        # time to wait until a packet from the same origin is relayed again
        self.store_block_time = 100000  # old way


        '''CONNECTION CHECK'''
        # interval when to check for inactivity of nodes
        self.last_connection_check = 0
        self.interval_connection_check = 1000*60*5
        # number of packets since last connection check
        self.num_packets_received_connection_check = np.zeros((100))
        # number of packets since last JOIN
        self.num_packets_received_after_join = np.zeros((100))

        '''
        RECEIVE CHECK
        '''
        # if a receive check was carried out during this interval
        self.receive_check_complete = False
        # nr of DATA packets received in one interval
        self.num_packets_received_interval = np.zeros((100))
        # packets that were missing int he last interval
        self.missing_interval_packets = []
        # cleanup of all variables used in receive check
        self.receive_check_cleanup = False


        '''
        STATISTICS
        '''
        # not received on first try
        self.num_not_received_on_first_try = 0
        # tx_cnt after the network was successfully started
        self.num_tx_after_start = 0
        # rx_cnt after the network was successfully started
        self.num_rx_after_start = 0
        # time when network was started successfully
        self.time_started = 0
        # time when the network was last restarted
        self.time_restarted = 0
        # number of nodes that rejoined
        self.num_joins = 0

        '''SENDING PARAMS'''
        # packet id stuff
        self.next_packet_id = 0

        '''DB CONNECTION'''
        if(not db_name is None):
            self.db = packet_db(db_name, self.logger)

    # get next free packet id
    # counting up until 255 then return to 0
    # should be enouh to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    # check packet for corruption
    # returns True if packet is okay
    def check_packet(self, rx_packet : packet) -> bool:

        if (rx_packet.payload_type == Payload_type.DATA and rx_packet.get_length() != 17 + 9):
            self.logger.log("  DATA packet was corrupted!", 3)
        elif (rx_packet.payload_type == Payload_type.JOIN_ACK and rx_packet.get_length() != 2 + 9):
            self.logger.log("  JOIN_ACK packet was corrupted!", 3)
        elif (rx_packet.payload_type == Payload_type.ACK and rx_packet.get_length() != 1 + 9):
            self.logger.log("  ACK packet was corrupted!", 3)
        elif (rx_packet.payload_type == Payload_type.ROUTE and rx_packet.get_length() != 7 + 9):
            self.logger.log("  ROUTE packet was corrupted!", 3)
        elif (rx_packet.payload_type == Payload_type.JOIN and rx_packet.get_length() != 2 + 9):
            self.logger.log("  JOIN packet was corrupted!", 3)
        elif (rx_packet.payload_type == Payload_type.COMMAND  or rx_packet.payload_type == Payload_type.COMMAND_ACK ): 
            
            if(rx_packet.get_length() < 1 + 9):
                self.logger.log("  COMMAND packet was corrupted!", 3)
            elif (rx_packet.payload[0] == Command_type.REQUEST.value.tobytes() and rx_packet.get_length() != 1 + 9):
                self.logger.log("  REQUEST packet was corrupted!", 3)
            elif (rx_packet.payload[0] == Command_type.SET_INTERVAL.value.tobytes() and rx_packet.get_length() != 18 + 9):
                self.logger.log("  SET_INTERVAL packet was corrupted!", 3)
            elif (rx_packet.payload[0] == Command_type.RESYNC_INTERVAL.value.tobytes() and rx_packet.get_length() != 5 + 9):
                self.logger.log("  RESYNC_INTERVAL packet was corrupted!", 3)
            elif (rx_packet.payload[0] == Command_type.SET_DISTANCE.value.tobytes() and rx_packet.get_length() != 2 + 9):
                self.logger.log("  SET_DISTANCE packet was corrupted!", 3)
            elif (rx_packet.payload[0] == Command_type.SET_BLOCK.value.tobytes() and rx_packet.get_length() != 2 + 9):
                self.logger.log("  SET_BLOCK packet was corrupted!", 3)
            elif ( not (rx_packet.payload[0] == Command_type.SET_BLOCK.value.tobytes() or rx_packet.payload[0] == Command_type.SET_DISTANCE.value.tobytes() or 
                        rx_packet.payload[0] == Command_type.RESYNC_INTERVAL.value.tobytes() or rx_packet.payload[0] == Command_type.SET_INTERVAL.value.tobytes() or 
                        rx_packet.payload[0] == Command_type.REQUEST.value.tobytes()) and rx_packet.get_length() != 1 + 9):
                self.logger.log("  COMMAND packet was corrupted!", 3)
            else:
                return True
        else:
            return True
        
        return False

    def receive(self, data, snr, rssi) -> None:
        p = self.parse_packet(data, snr, rssi) 
        if( ( p.target == 0 or p.target == self.id ) and not (p.origin == self.id) ):
            # check artificial blocks
            if(p.sender in self.artificial_blocks):
                self.logger.log("  not handling packet from %i (sender: %i) because of artificial block" % (p.origin, p.sender), 3)
            elif(len(self.white_list) > 0 and not ( int(p.origin) in self.white_list) ):
                self.logger.log("  not handling packet from %i because not in white-list" % p.origin, 3)
            else:
                # check for corruption
                if(self.check_packet(p)):
                    self.handle_packet(p)
        else:
            if(p.origin == self.id):
                self.logger.log("  not handling %s packet sent by %i, because I sent it" % (str(p.payload_type), p.sender), 4)
            else:
                self.logger.log("  not handling %s packet from %i (sender: %i), because wrong target: %i" % (str(p.payload_type), p.origin, p.sender, p.target), 3)
            pass

    def parse_packet(self, data, snr, rssi) -> packet:

        app_id = data[:2]
        sender = data[2]
        origin = data[3]
        target = data[4]
        max_hops = data[5]>>4
        num_hops = data[5]&15
        p_id = data[6]
        dir = data[7]>>7 == 1
        last_distance = data[7]&127
        pl_type = Payload_type.from_byte(data[8])

        if(len(data) > 9):
            payload = data[9:]
        else:
            payload = None

        self.logger.log("    %s from node %i (pid=%i)" % (str(pl_type), origin, p_id), 4)
        
        self.logger.log("  Sender: %i" % data[2], 4)
        self.logger.log("  Origin: %i" % data[3], 4)
        self.logger.log("  Target: %i" % data[4], 4)
        self.logger.log("  Hops: %i / %i" % (data[5]&15, data[5]>>4), 4)
        self.logger.log("  Packet-ID: %i" % data[6], 4)
        self.logger.log("  Dir: %i, last_dist: %i" % ( data[7]>>7, data[7]&127 ), 4)
        self.logger.log("  PL-Type: %s (%i)" % ( str(pl_type), data[8]), 4)

        return packet(app_id, sender, target, max_hops, p_id, last_distance, dir, pl_type, payload, num_hops=num_hops, snr=snr, rssi=rssi, origin=origin)
    
    def handle_packet(self, rx_packet: packet):

        if(self.check_multiple_packet(rx_packet)):

            if(rx_packet.origin in self.node_ids):
                idx = self.node_ids.index(rx_packet.origin)
                self.last_connection[idx] = self.get_time()

            if(rx_packet.payload_type == Payload_type.DATA):

                self.logger.log("  %s from node %i (pid=%i, last sender=%i)" % (str(rx_packet.payload_type), rx_packet.origin, rx_packet.packet_id, rx_packet.sender ), 2)

                if(not rx_packet.payload is None and len(rx_packet.payload) > 15):
                    # store in db
                    self.db.store_data(rx_packet)
                    # update link quality statistics
                    if(rx_packet.origin in self.node_ids):
                        idx = self.node_ids.index(rx_packet.origin)
                    
                        self.num_packets_received[idx] += 1
                        self.num_packets_received_connection_check[idx] += 1
                        self.num_packets_received_interval[idx] += 1
                        self.num_packets_received_after_join[idx] += 1
                        self.last_connection[idx] = self.get_time()

                        if(self.successfully_started):
                            self.num_rx_after_start += 1

                        # update current battery level
                        self.node_battery_level[idx] = rx_packet.payload[16]
                    else:
                        self.logger.log("ERROR: Sender not connected to this central station", 1)
                else:
                    self.logger.log("ERROR: packet was corrupted during transmission", 1)

            elif(rx_packet.payload_type == Payload_type.JOIN):
                self.logger.log("  receiving join request from node with ID: %i with RSSI:%i --> first contact: (RSSI: %i, NID: %i)" % (rx_packet.origin, rx_packet.rssi, rx_packet.payload[0], rx_packet.payload[1]), 2)  
                
                self.received_join_requests[self.num_received_join_requests] = rx_packet.origin

                # if packet has not been relayed
                # payload of packet (=RSSI of first relay) is 0
                if(rx_packet.payload[0] == 0):
                    self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.rssi
                    self.received_join_requests_first_node[self.num_received_join_requests] = self.id
                else:
                    self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.payload[0]
                    self.received_join_requests_first_node[self.num_received_join_requests] = rx_packet.payload[1]

                # add id to list if not already received
                if(not rx_packet.origin in self.nodes_joined_last_interval):
                    self.nodes_joined_last_interval.append(rx_packet.origin)

                # removed REQEST as they will get set to finished anyways
                self.command_center.remove_commands_for_node(rx_packet.origin, [Command_type.JOIN_ACK])

                self.num_received_join_requests += 1 

                # reset sending status if node is rejoining
                if(rx_packet.origin in self.node_ids):
                    idx = self.node_ids.index(rx_packet.origin)
                    self.node_sending_status[idx] = False
                    self.node_sleeping_status[idx] = False


            elif(rx_packet.payload_type is Payload_type.ACK):
                self.logger.log("  receiving ACK from node %i" % rx_packet.origin, 2)

            elif( rx_packet.payload_type is Payload_type.ROUTE ):
                route = []
                route.append(rx_packet.origin)
                for i in range(rx_packet.num_hops -1):
                    route.append(rx_packet.payload[i])
                route.append(self.id)
                
                self.routes.append(route)

                self.logger.log("  Central: received ROUTE-packet: %s" % route, 2)

            # handle at command center
            self.command_center.handle_packet(rx_packet)      
        else:
            self.logger.log("  Central: not handling packet %s from node %i because it was received multiple times (last sender=%i)" % (str(rx_packet.payload_type), rx_packet.origin, rx_packet.sender), 3)

    def send_packet(self, packet: packet, retry=3): 
        packet.sender = self.id
        # Set module in send mode
        if(retry > 0):
            try:
                self.lora.set_config('lorap2p:transfer_mode:2')
                data = packet.to_bytes()
                self.lora.send_p2p(data)
                # back to receive
                self.lora.set_config('lorap2p:transfer_mode:1')
            except Rak811TimeoutError:
                self.logger.log("ERROR WHILE SENDING, RETRYING...", 1)
                self.send_packet(packet, retry-1)
            except Rak811ResponseError:
                self.logger.log("ERROR WHILE SENDING, RETRYING...", 1)
                self.send_packet(packet, retry-1)
        else:
            raise Rak811TimeoutError('Multiple timeouts while waiting for data')

    def remove_node(self, nid : int):

        removed_idx = self.node_ids.index(nid)
        self.command_center.remove_commands_for_node(nid)

        # move last node to index of removed node if nde is not last in list
        # this way only one SET_INTERVAL COMMAND is required
        if(removed_idx < self.num_connected_nodes - 1):
            self.node_battery_level[removed_idx] = self.node_battery_level[self.num_connected_nodes - 1]
            self.node_sending_status[removed_idx] = self.node_sending_status[self.num_connected_nodes - 1]
            self.node_sleeping_status[removed_idx] = self.node_sleeping_status[self.num_connected_nodes - 1]
            self.node_wanted_sleeping_status[removed_idx] = self.node_wanted_sleeping_status[self.num_connected_nodes - 1]
            self.node_distances[removed_idx] = self.node_distances[self.num_connected_nodes - 1]
            self.node_ids[removed_idx] = self.node_ids[self.num_connected_nodes - 1]
            self.node_interval_sent[removed_idx] = self.node_interval_sent[self.num_connected_nodes - 1]
            self.node_of_first_contact[removed_idx] = self.node_of_first_contact[self.num_connected_nodes - 1]
            self.num_packets_received[removed_idx] = self.num_packets_received[self.num_connected_nodes - 1] 
            self.num_packets_received_connection_check[removed_idx] = self.num_packets_received_connection_check[self.num_connected_nodes -1]
            self.num_packets_received_interval[removed_idx] = self.num_packets_received_interval[self.num_connected_nodes - 1]
            self.num_packets_received_after_join[removed_idx] = self.num_packets_received_after_join[self.num_connected_nodes - 1]
            self.first_connection[removed_idx] = self.first_connection[self.num_connected_nodes - 1]
            
            # remove from last_connection 
            self.last_connection[removed_idx] = self.last_connection[self.num_connected_nodes - 1]
            # interval data needs to be sent again
            self.node_interval_ack[removed_idx] = False
            # schedule interval data for node with moved slot
            self.command_center.register_command(set_interval_command(
                    self.node_ids[removed_idx],
                    prio=1,
                    retry_sending=True,
                    one_interval=False
                ))

        # remove last entry
        self.node_battery_level.pop(self.num_connected_nodes - 1)
        self.node_sending_status.pop(self.num_connected_nodes - 1)
        self.node_sleeping_status.pop(self.num_connected_nodes - 1)
        self.node_wanted_sleeping_status.pop(self.num_connected_nodes - 1)
        self.node_distances.pop(self.num_connected_nodes - 1)
        self.node_ids.pop(self.num_connected_nodes - 1)
        self.node_of_first_contact.pop(self.num_connected_nodes - 1)
        self.node_interval_ack.pop(self.num_connected_nodes - 1)
        self.node_interval_sent.pop(self.num_connected_nodes - 1)

        self.last_connection[self.num_connected_nodes - 1] = 0
        self.first_connection[self.num_connected_nodes - 1] = 0
        self.num_packets_received[self.num_connected_nodes - 1] = 0
        self.num_packets_received_connection_check[self.num_connected_nodes - 1]= 0
        self.num_packets_received_interval[self.num_connected_nodes - 1] = 0
        self.num_packets_received_after_join[self.num_connected_nodes - 1] = 0
        # decrease counter
        self.num_connected_nodes -= 1


    def update_loop(self) -> None:

        # Executed once at the start of each interval
        time = self.get_time()
        if(time > self.next_interval_start - 1):
            
            '''
            RESET VARIABLES
            Set up state for the beginning of the new interval
            '''
            self.last_interval_start = self.next_interval_start
            self.next_interval_start = self.last_interval_start + self.interval

            self.receive_check_complete = False
            self.receive_check_cleanup = False

            self.state_restored = False

            self.logger.log("---> START interval: %s" % (datetime.fromtimestamp(int(self.get_time()/1000)).strftime("%H:%M:%S")), 1)
            self.logger.log("next interval: %s (%i)" % (datetime.fromtimestamp(int(self.next_interval_start/1000)).strftime("%H:%M:%S"), self.next_interval_start), 1)

            self.interval_count += 1

            '''
            CONNECTION CHECK
            check node connection status
            if not received packet in last 45 min, remove node from connected nodes
            - only removes one node per interval
            - only removes nodes with node_sending_status[idx] == True
            - does not remove nodes that are rejoining again (node_inderval_ack[idx] == False)
            '''
            if(self.successfully_started):
                refactor_network = False
                removed_idx = 0
                for i in range(self.num_connected_nodes):
                    # self.node_interval_ack[i] and 
                    # this prevents removal of last node because this node was sent an SET_INTERVAL packet because the network was refactored before
                    # self.node_sending_status[i] and
                    # this keeps nodes that loose connection while rejoining
                    if(self.get_time() - self.last_connection[i] > 1000*60*45):
                        refactor_network = True
                        removed_idx = i
                        break

                if(refactor_network):
                    self.logger.log("Removing node %s because of inactivity" % (self.node_ids[removed_idx]), 2)
                    self.remove_node(self.node_ids[removed_idx])


            if(self.interval_count % self.interval_resync_after == 0):
                self.logger.log("  RESYNCING INTERVAL DATA!", 1)
                # queue resync interval command
                self.command_center.register_command(resync_interval_command(0) )

            # save state
            self.save_state()

            # update overall sleeping status
            self.nodes_sleeping = False
            for i in range(self.num_connected_nodes):
                if(self.node_sleeping_status[i]):
                    self.nodes_sleeping = True
                    break

            # update overall sending status
            self.all_nodes_sending = True
            if(self.num_connected_nodes == 0): self.all_nodes_sending = False
            for i in range(self.num_connected_nodes):
                if(not self.node_sending_status[i]):
                    self.all_nodes_sending = False
                    break

            # values after updating
            self.logger.log("-> num connected nodes:   %i" % self.num_connected_nodes, 1)
            self.logger.log("-> successfully started:  %s" % self.successfully_started, 1)
            self.logger.log("-> network running:       %s" % self.network_running, 1)
            self.logger.log("-> nodes sending:         %s" % self.nodes_started_sending, 1)
            self.logger.log("-> all nodes sending:     %s" % self.all_nodes_sending, 1)
            self.logger.log("-> nodes sleeping:        %s" % self.nodes_sleeping, 1)
            self.logger.log("-> new nodes:             %s" % self.new_nodes_to_join, 1)

        ''' 
        JOIN REQUESTS
        handle all join requests that were received in the last interval
        '''
        if(self.get_time() - self.last_join_check > self.interval_join_check):

            self.logger.log("  JOIN CHECK:", 2 if (self.num_empty_join_intervals < 4 or self.num_received_join_requests > 0) else 4)
            self.logger.log("    received %i join requests" % self.num_received_join_requests, 2 if (self.num_empty_join_intervals < 4 or self.num_received_join_requests > 0) else 4)

            # if the nodes started sending the JOIN requests are scheduled to avoid
            # the sending interval
            # when the nodes are sleeping they are only handled once every interval
            if(self.nodes_started_sending):
                if(self.nodes_sleeping):
                    self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
                else:
                    self.last_join_check += self.interval_join_check
                    if(self.last_join_check > self.next_interval_start - self.interval_join_check - 30*1000 and self.last_join_check < self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width):
                        self.logger.log("    Setting JOIN-CHECK to end of send-interval", 2)
                        self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
            else:
                self.last_join_check += self.interval_join_check

            node_to_join = None
            node_to_join_dist = 1
            node_to_join_first_node = self.id
            
            '''
            decide which nodes should be allowed to join next

            always add the node with the lowest RSSI
            only add one node at a time
            
            TWO MODES:
            dynamic:
            -get distance of node (B) that received the JOIN request
            -assign node (A) the distance of node (B) + 1

            pre-assigned:
            -if node in self.assigned_distances
            -assign node that distance
            '''
            # received a JOIN request directly at central
            if(self.num_received_join_requests > 0):

                idx = np.argmax(self.received_join_requests_rssi[:self.num_received_join_requests])
                
                self.num_empty_join_intervals = 0
                self.new_nodes_to_join = True
                self.all_nodes_sending = False
                self.network_running = False

                node_to_join = int(self.received_join_requests[idx])
                node_to_join_first_node = self.received_join_requests_first_node[idx]

                if(node_to_join in self.node_ids):
                    node_to_join_dist = self.node_distances[self.node_ids.index(self.received_join_requests[idx])]
                else: #(not node_to_join_first_node == self.id):
                    if(("%i" % node_to_join) in self.assigned_distances):
                        node_to_join_dist = self.assigned_distances.get("%i" % node_to_join)
                    elif(not node_to_join_first_node == self.id):
                        node_to_join_dist = self.node_distances[self.node_ids.index(int(node_to_join_first_node))] + 1

                # update connected node parameters
                # and
                # send the join requests
                if(not node_to_join in self.node_ids):
                    self.num_connected_nodes += 1
                    self.first_connection[self.num_connected_nodes-1] = self.get_time()
                    self.node_ids.append(int(node_to_join))
                    self.node_battery_level.append(-1)
                    self.node_distances.append(node_to_join_dist)
                    self.node_of_first_contact.append(node_to_join_first_node)
                    self.node_sending_status.append(False)
                    self.node_sleeping_status.append(False)
                    self.node_wanted_sleeping_status.append(False)
                    # not sent and accepted interval
                    self.node_interval_sent.append(False)
                    self.node_interval_ack.append(False)
                else:
                    self.logger.log("    Node %i: rejoining" % node_to_join, 1)
                    idx = self.node_ids.index(node_to_join)
                    self.node_interval_sent[idx] = False
                    self.node_interval_ack[idx] = False
                    self.node_sending_status[idx] = False
                    self.node_sleeping_status[idx] = False
                    self.num_packets_received_after_join[idx] = 0

                self.command_center.register_command(ack_join_command(
                        node_to_join,
                        node_to_join_dist,
                        self.id
                    ))

            else:
                self.num_empty_join_intervals += 1

            # reset join info
            self.received_join_requests = np.zeros((100))
            self.received_join_requests_rssi = np.zeros((100))
            self.received_join_requests_first_node = np.zeros((100))
            self.num_received_join_requests = 0

        ''' 
        INTERVAL
        Send the interval data out
        '''
        if(self.new_nodes_to_join and (self.num_empty_join_intervals >= self.required_num_emtpy_join) ):
           
            if(self.get_time() - self.last_interval_broadcast > self.interval_broadcast and self.next_interval_start - self.get_time() > self.num_connected_nodes*self.interval_slot_width):
                self.logger.log("  INTERVAL-CHECK", 2)
                # if the nodes started sending the JOIN requests are scheduled to avoid
                # the sending interval
                # when the nodes are sleeping they are only handled once every interval
                if(self.nodes_started_sending):
                    if(self.nodes_sleeping):
                        self.last_interval_broadcast = self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width
                    else:
                        self.last_interval_broadcast += self.interval_broadcast
                        if(self.last_interval_broadcast > self.next_interval_start - self.last_interval_broadcast - 30*1000 and self.last_interval_broadcast < self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width):
                            self.logger.log("    Setting INTERVAL-CHECK to end of send-interval", 2)
                            self.last_interval_broadcast = self.next_interval_start - self.last_interval_broadcast + self.num_connected_nodes*self.interval_slot_width
                        elif(self.last_interval_broadcast < self.get_time() - 1000):
                            self.logger.log("    Resetting INTERVAL-CHECK", 2)
                            self.last_interval_broadcast = self.get_time()
                else:
                    self.last_interval_broadcast += self.interval_broadcast

                sent_int = []
                for i in range(len(self.node_ids)):
                    # change required_new_empty_join to 0 after start
                    # then check here if node_id in received joins
                    if(not self.node_interval_sent[i] and not self.node_ids[i] in self.nodes_joined_last_interval):
                        sent_int.append(self.node_ids[i])
                        self.command_center.register_command(set_interval_command(
                            self.node_ids[i],
                            prio=1,
                            retry_sending=True,
                            one_interval=False
                        ))
                        self.node_interval_sent[i] = True
                        self.num_joins += 1

                # reset join interval counter
                self.nodes_joined_last_interval = []

                if(len(sent_int) > 0): self.logger.log("  Sending interval data to nodes %s" % str(sent_int), 2)

                # check if all have ACK
                all_reached = True
                for i in range(len(self.node_ids)):
                    if(not self.node_interval_ack[i]):
                        all_reached = False
                        break

                # update logic, all connected nodes have sent ACK
                if(all_reached):
                    self.logger.log("  Central: All connected nodes have ACK the interval", 1)
                    self.nodes_started_sending = True
                    self.new_nodes_to_join = False
                    # reduce number of required empty join intervals for faster rejoining of nodes
                    self.required_num_emtpy_join = 1

                    if(not self.successfully_started):
                        self.logger.log("  Sending first START_SENDING to nodes", 1)
                        # disable receive check for this itnerval
                        self.receive_check_cleanup = True
                        self.receive_check_complete = True
                        # send 3 START_SENDING broadcasts
                        for i in range(3):

                            self.command_center.register_command(nack_command(
                                0,
                                Command_type.START_SENDING,
                                prio = 2,
                                one_interval=True
                            ))
                    elif(not self.all_nodes_sending):
                        self.logger.log("  Sending START_SENDING to nodes", 1)
                        # send 1 START_SENDING broadcasts
                        self.command_center.register_command(nack_command(
                            0,
                            Command_type.START_SENDING,
                            prio = 2,
                            one_interval=True
                        ))

        '''
        RECEIVE CHECK
        executed once every interval
        after all nodes have sent data
        '''
        if( (not self.state_restored) and self.nodes_started_sending and not self.receive_check_complete and self.last_interval_start + self.interval_slot_width*self.num_connected_nodes < self.get_time()):

            # check the apckets that were received in this interval and compare against the packets that should have been received
            # if packet is missing, queue REQUEST command
            if(self.successfully_started):
                self.logger.log("  checking the received packets", 2)
                self.num_tx_after_start += self.num_connected_nodes
                
                nodes = "    Node:".ljust(14)
                rec_pkt = "    Received:".ljust(14)
                for i in range(self.num_connected_nodes):
                    nodes += str(self.node_ids[i]).rjust(4)
                    # display d if node has disabled sending via command
                    if(self.node_sending_status[i]):
                        rec_pkt += str(int(self.num_packets_received_interval[i])).rjust(4)
                    else:
                        rec_pkt += "d".rjust(4)
                        # remove nodes that are not sending from the statistics
                        self.num_tx_after_start -= 1

                self.logger.log(nodes, 2)
                self.logger.log(rec_pkt, 2)

                for i in range(self.num_connected_nodes):
                    if(self.num_packets_received_interval[i] == 0 and self.node_sending_status[i]):
                        self.logger.log("    Missing packet from node: %i" % self.node_ids[i], 2)
                        self.missing_interval_packets.append(self.node_ids[i])
                        self.num_not_received_on_first_try += 1

                self.receive_check_complete = True

                for i in range(len(self.missing_interval_packets)):
                    self.command_center.register_command(request_command(self.missing_interval_packets[i], retry_sending=True))

            # check if at least one data packet from all nodes has been received after they joined.
            # if so, the network was successfully (re-)started
            if(not self.successfully_started or (self.successfully_started and not self.network_running)):
                self.logger.log("  checking the received packets after joining", 2)
                
                nodes = "    Node:".ljust(14)
                rec_pkt = "    Received:".ljust(14)
                all_sending = True

                for i in range(self.num_connected_nodes):
                    nodes += str(self.node_ids[i]).rjust(4)
                    # display d if node has disabled sending via command
                    if(self.node_sending_status[i]):
                        rec_pkt += str(int(self.num_packets_received_after_join[i])).rjust(4)
                    else:
                        rec_pkt += "d".rjust(4)

                    if(self.num_packets_received_after_join[i] == 0):
                        all_sending = False

                self.logger.log(nodes, 2)
                self.logger.log(rec_pkt, 2)

                if(all_sending):
                    if (not self.successfully_started):
                        self.logger.log("  SUCCESSFULLY STARTED THE NETWORK", 1)
                        self.successfully_started = True
                        self.required_num_emtpy_join = 1
                        self.time_started = self.get_time()
                    else:
                        self.logger.log("  SUCCESSFULLY RESTARTED THE NETWORK", 1)
                        self.time_restarted = self.get_time()
                        for i in range(len(self.node_ids)):
                            if(not (self.node_wanted_sleeping_status[i] == self.node_sleeping_status[i]) ):
                                self.command_center.register_command(ack_command(
                                    self.node_ids[i],
                                    Command_type.ENABLE_SLEEP if self.node_wanted_sleeping_status[i] else Command_type.DISABLE_SLEEP,
                                    prio = 2
                                ))
                    
                    self.network_running = True
                    self.last_connection_check = self.get_time()
                    # update timing parameters for the JOIN and INTERVAL_BROPADCAST routines
                    # they are now executed once at the beginning of each interval
                    # DONE distributed in sub-routines
                elif( not self.successfully_started):
                    self.logger.log("  Sending START_SENDING to nodes", 3)
                    # send 1 START_SENDING broadcasts to reach missing nodes

                    self.command_center.register_command(nack_command(
                        0,
                        Command_type.START_SENDING,
                        prio = 2,
                        one_interval=True
                    ))

                self.receive_check_complete = True
        
        '''
        FINISH RECEIVE CHECK
        
        executed once every interval
        at the end of the active time of the current interval
        '''
        # self.successfully_started and 
        if(self.receive_check_complete and not self.receive_check_cleanup and self.last_interval_start + self.interval_slot_width*self.num_connected_nodes + self.interval_active_extension < self.get_time()):
            
            self.logger.log("  cleaning up receive-check")
            self.num_packets_received_interval = np.zeros((100))
            self.missing_interval_packets = []
            self.num_packets_received_interval = np.zeros((100))
            self.receive_check_cleanup = True
            self.logger.log("<--- END of active part of interval")

        '''
        COMMAND CENTER
        '''
        # if(self.nodes_started_sending):
        self.command_center.update()

        # check packet queue
        self.update_queue()

    def update_queue(self):
        if(len(self.packet_queue) > 0):
            #self.logger.log("updating delayed packets %i" % len(self.packet_queue), 4)
            remove = []
            for i in range(0, len(self.packet_queue)):
                if(self.get_time() - self.packet_queue_timer[i] > 0):
                    self.logger.log("  Central: sending delayed packet to node %i" % self.packet_queue[i].target, 4)
                    remove.append(i)
                    self.send_packet(self.packet_queue[i])
                    
            for i in range(len(remove)):
                self.packet_queue_timer.pop(remove[i]- i)
                self.packet_queue.pop(remove[i]- i)

    def queue_packet(self, packet, time):
        self.packet_queue.append(packet)
        self.packet_queue_timer.append(self.get_time() + time)

    def get_time(self) -> int:
        return round(datetime.now().timestamp() * 1000)

    # checks if this packet has already been received
    # returns handle packet? --> True / False
    def check_multiple_packet(self, rx_packet: packet):

         #check if forwarded packet from this origin in the last time
        remove = []
        largest_blocking_time = 0
        num_blocks = 0

        # no blocking of ROUTE or JOIN packages as they are supposed to be received multiple times
        if(rx_packet.payload_type == Payload_type.ROUTE or rx_packet.payload_type == Payload_type.JOIN):
            return True

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
            self.logger.log(self.last_packet_origins, 5)
            self.logger.log("removing %i" % (remove[i]-i), 5)
            self.last_packet_relay.pop(remove[i]-i)
            self.last_packet_origins.pop(remove[i]-i)
            self.last_packet_pid.pop(remove[i]-i)
            self.logger.log(self.last_packet_origins, 5)

        if(num_blocks > 0):
            return False
        else:
            self.last_packet_relay.append(self.get_time())
            self.last_packet_origins.append(rx_packet.origin)
            self.last_packet_pid.append(rx_packet.packet_id)
            return True

    # remove all join requests received from node with ID: nid
    # called by JOIN_ACK command at execution
    # to prevent double sending
    def remove_received_join_requests(self, nid : int) -> None:
        
        if(self.num_received_join_requests > 0):
            self.logger.log("  removing join requests from node %i" % nid, 3)
            idxs_stay = []
            for i in range(self.num_received_join_requests):
                if(int(self.received_join_requests[i]) != nid): 
                    idxs_stay.append(i)

            if(len(idxs_stay) > 0):
                new_received_join_requests = self.received_join_requests[idxs_stay]
                new_received_join_requests_rssi = self.received_join_requests_rssi[idxs_stay]
                new_received_join_requests_first_node = self.received_join_requests_first_node[idxs_stay]

            self.received_join_requests = np.zeros((100))
            self.received_join_requests_rssi = np.zeros((100))
            self.received_join_requests_first_node = np.zeros((100))

            if(len(idxs_stay) > 0):
                self.received_join_requests[:len(new_received_join_requests)] = new_received_join_requests
                self.received_join_requests_rssi[:len(new_received_join_requests_rssi)] = new_received_join_requests_rssi
                self.received_join_requests_first_node[:len(new_received_join_requests_first_node)] = new_received_join_requests_first_node 

            self.logger.log("  removed %i join requests" % (self.num_received_join_requests - len(idxs_stay)), 3)
            self.num_received_join_requests = len(idxs_stay)

    def save_state(self):
        self.logger.log("Packet_handler: saving state!", 1)
        config = {
            "time" : self.get_time(),
            "packet_handler" : self.write_state()
        }
        with open("last_state.pkl", "wb") as f:
            pickle.dump(config, f)

    def restore_state(self, d : dict) -> None:

        self.interval = d.get("interval")

        # self.next_interval_start = d.get("next_interval_start")
        # self.last_interval_start = d.get("last_interval_start")
        self.interval_slot_width = d.get("interval_slot_width")
        self.interval_active_extension = d.get("interval_active_extension")

        '''JOIN PARAMS'''
        self.last_join_check = d.get("last_join_check")
        self.interval_join_check = d.get("interval_join_check")
        self.num_received_join_requests = d.get("num_received_join_requests")
        self.received_join_requests = d.get("received_join_requests")
        self.received_join_requests_rssi = d.get("received_join_requests_rssi")
        self.received_join_requests_first_node = d.get("received_join_requests_first_node")
        self.new_nodes_to_join = d.get("new_nodes_to_join")
        # self.num_empty_join_intervals = d.get("num_empty_join_intervals")
        self.required_num_emtpy_join = d.get("required_num_emtpy_join")
        self.nodes_joined_last_interval = d.get("nodes_joined_last_interval")

        '''INTERVAL SYNC PARAMS'''
        self.node_interval_ack = d.get("node_interval_ack")
        self.node_interval_sent = d.get("node_interval_sent")
        self.interval_broadcast = d.get("interval_broadcast")
        self.last_interval_broadcast = d.get("last_interval_broadcast")
        self.nodes_started_sending = d.get("nodes_started_sending")

        '''NETWORK PARAMS'''
        self.all_nodes_sending = d.get("all_nodes_sending")
        self.successfully_started = d.get("successfully_started")
        self.network_running = d.get("network_running")
        self.nodes_sleeping = d.get("nodes_sleeping")
        self.num_connected_nodes = d.get("num_connected_nodes")
        self.first_connection = d.get("first_connection")
        self.last_connection = d.get("last_connection")
        self.num_packets_received = d.get("num_packets_received")
        self.num_packets_received_interval = d.get("num_packets_received_interval")
        self.node_ids = d.get("node_ids")
        self.node_distances = d.get("node_distances")
        self.node_of_first_contact = d.get("node_of_first_contact")
        self.node_battery_level = d.get("node_battery_level")
        self.node_sending_status = d.get("node_sending_status")
        self.node_sleeping_status = d.get("node_sleeping_status")
        self.node_wanted_sleeping_status = d.get("node_wanted_sleeping_status")

        '''DUPLICATE DETECTION'''
        self.last_packet_origins = d.get("last_packet_origins")
        self.last_packet_relay = d.get("last_packet_relay")
        self.last_packet_pid = d.get("last_packet_pid")
        self.store_block_time = d.get("store_block_time")


        '''CONNECTION CHECK'''
        self.last_connection_check = d.get("last_connection_check")
        self.interval_connection_check = d.get("interval_connection_check")
        self.num_packets_received_connection_check = d.get("num_packets_received_connection_check")
        self.num_packets_received_after_join = d.get("num_packets_received_after_join")

        '''RECEIVE CHECK'''
        # self.receive_check_complete = d.get("receive_check_complete")
        # self.num_packets_received_interval = d.get("num_packets_received_interval")
        # self.missing_interval_packets = d.get("missing_interval_packets")
        # self.receive_check_cleanup  = d.get("receive_check_cleanup")
        self.receive_check_cleanup = True

        '''STATISTICS'''
        self.num_not_received_on_first_try = d.get("num_not_received_on_first_try")
        self.num_tx_after_start = d.get("num_tx_after_start")
        self.num_rx_after_start = d.get("num_rx_after_start")
        self.time_started = d.get("time_started")
        self.time_restarted = d.get("time_restarted")
        self.num_joins = d.get("num_joins")

        '''SENDING PARAMS'''
        self.next_packet_id  = d.get("next_packet_id")
        
        # update intervals
        if(self.nodes_started_sending):
            if(self.nodes_sleeping):
                self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
            else:
                self.last_join_check = self.get_time()
                if(self.last_join_check > self.next_interval_start - self.interval_join_check - 30*1000 and self.last_join_check < self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width):
                    self.logger.log("  setting join-check to end of send-interval", 2)
                    self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
        else:
            self.last_join_check = self.get_time()

        if(self.nodes_started_sending):

            if(self.nodes_sleeping):
                self.last_interval_broadcast = self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width
            else:
                self.last_interval_broadcast = self.get_time()
                if(self.last_interval_broadcast > self.next_interval_start - self.last_interval_broadcast - 30*1000 and self.last_interval_broadcast < self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width):
                    self.logger.log("  setting interval-check to end of send-interval", 2)
                    self.last_interval_broadcast = self.next_interval_start - self.last_interval_broadcast + self.num_connected_nodes*self.interval_slot_width
        else:
            self.last_interval_broadcast = self.get_time()


        self.logger.log("RESTORED STATE")
        # values after updating
        self.logger.log("-> num connected nodes:   %i" % self.num_connected_nodes, 1)
        self.logger.log("-> successfully started:  %s" % self.successfully_started, 1)
        self.logger.log("-> network running:       %s" % self.network_running, 1)
        self.logger.log("-> nodes sending:         %s" % self.nodes_started_sending, 1)
        self.logger.log("-> all nodes sending:     %s" % self.all_nodes_sending, 1)
        self.logger.log("-> nodes sleeping:        %s" % self.nodes_sleeping, 1)
        self.logger.log("-> new nodes:             %s" % self.new_nodes_to_join, 1)

        self.logger.log("-> node_ids:              %s" % str(self.node_ids) , 1)
        self.logger.log("-> node_distances:        %s" % str(self.node_distances), 1)

        self.state_restored = True

    def write_state(self) -> dict:

        # ToDo
        # - remove ack_interval from nodes that still have set_interval command pending in Command_center

        d = {
            #INTERVAL
            "interval" : self.interval,

            "next_interval_start" : self.next_interval_start,
            "last_interval_start" : self.last_interval_start,
            "interval_slot_width" : self.interval_slot_width,
            "interval_active_extension" : self.interval_active_extension,

            #JOIN PARAMS
            "last_join_check" : self.last_join_check,
            "interval_join_check" : self.interval_join_check,
            "num_received_join_requests" : self.num_received_join_requests,
            "received_join_requests" : self.received_join_requests,
            "received_join_requests_rssi" : self.received_join_requests_rssi,
            "received_join_requests_first_node" : self.received_join_requests_first_node,
            "new_nodes_to_join" : self.new_nodes_to_join,
            "num_empty_join_intervals" : self.num_empty_join_intervals,
            "required_num_emtpy_join" : self.required_num_emtpy_join,
            "nodes_joined_last_interval" : self.nodes_joined_last_interval,

            #INTERVAL SYNC PARAMS
            "node_interval_ack" : self.node_interval_ack,
            "node_interval_sent" : self.node_interval_sent,
            "interval_broadcast" : self.interval_broadcast,
            "last_interval_broadcast" : self.last_interval_broadcast,
            "nodes_started_sending" : self.nodes_started_sending,

            #NETWORK PARAMS
            "all_nodes_sending" : self.all_nodes_sending,
            "successfully_started" : self.successfully_started,
            "network_running" : self.network_running,
            "nodes_sleeping" : self.nodes_sleeping,
            "num_connected_nodes" : self.num_connected_nodes,
            "first_connection" : self.first_connection,
            "last_connection" : self.last_connection,
            "num_packets_received" : self.num_packets_received,
            "num_packets_received_interval" : self.num_packets_received_interval,
            "node_ids" : self.node_ids,
            "node_distances" : self.node_distances,
            "node_of_first_contact" : self.node_of_first_contact,
            "node_battery_level" : self.node_battery_level,
            "node_sending_status" : self.node_sending_status,
            "node_sleeping_status" : self.node_sleeping_status,
            "node_wanted_sleeping_status" : self.node_wanted_sleeping_status,

            #DUPLICATE DETECTION
            "last_packet_origins" : self.last_packet_origins,
            "last_packet_relay" : self.last_packet_relay,
            "last_packet_pid" : self.last_packet_pid,
            "store_block_time" : self.store_block_time,

            #CONNECTION CHECK
            "last_connection_check" : self.last_connection_check,
            "interval_connection_check" : self.interval_connection_check,
            "num_packets_received_connection_check" : self.num_packets_received_connection_check,
            "num_packets_received_after_join" : self.num_packets_received_after_join,

            #RECEIVE CHECK
            "receive_check_complete" : self.receive_check_complete,
            "num_packets_received_interval" : self.num_packets_received_interval,
            "missing_interval_packets" : self.missing_interval_packets,
            "receive_check_cleanup" : self.receive_check_cleanup,

            #STATISTICS
            "num_not_received_on_first_try" : self.num_not_received_on_first_try,
            "num_tx_after_start" : self.num_tx_after_start,
            "num_rx_after_start" : self.num_rx_after_start,
            "time_started" : self.time_started,
            "time_restarted" : self.time_restarted,
            "num_joins" : self.num_joins,

            #SENDING PARAMS
            "next_packet_id" : self.next_packet_id 
        }

        return d