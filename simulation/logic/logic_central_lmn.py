from logic.command.command_center import command_center
from logic.command.action_center import action_center
from logic.command.command import request_command, nack_command, ack_command, reset_command, ack_join_command, set_interval_command, resync_interval_command
from logic.handler_lmn import handler_lmn
from hw.packet import Payload_type, Command_type
from hw.packet_dist import packet_dist
from logic.logic_central import logic_central

import numpy as np
from datetime import datetime

class logic_central_lmn(logic_central):

    def __init__(self, appID : int, node_id : int, db : bool=False, interval : int=1000*60*10, handler=handler_lmn(), blocks : list = [], spreading_f : int = 10) -> None:
        super().__init__(appID, node_id, db, handler)

        self.artificial_blocks = blocks

        '''COMMANDS'''
        # command priority and timing
        self.command_center : command_center = None
        # quue for bigger actions (= collection of consecutive commands)
        self.action_center : action_center = None

        '''INTERVAL PARAMETERS'''
         # interval in which nodes should broadcast
        self.interval = interval #interval
        # time the next interval will start
        # calculate that is always starts on an even minute
        self.next_interval_start = 0
        # time the last interval started
        self.last_interval_start = self.next_interval_start - self.interval
        # size of a sending_slot for one node
        self.interval_slot_width = int(1000*7.5)
        # time that the active interval time is extended to allow for other transmissions
        self.interval_active_extension = 1000*20

        '''JOIN PARAMS'''
        # time to wait for join requests to decide which node to add first
        # should be double the join repeat interval
        self.last_join_check = 0
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
        self.received_join_requests_first_node = np.ones((100))
        # new nodes to join
        self.new_nodes_to_join = False
        # ids of nodes that sent join in last interval
        self.nodes_joined_last_interval = []
        
        # number of consecutive join intervals without a new join request
        self.num_empty_join_intervals = 0
        # number of join intervals to switch to assign mode
        self.required_num_emtpy_join = 2

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
        self.assigned_distances : dict = {
            "1" : 1,
            "2" : 1,
            "3" : 2,
            "4" : 3,
            "5" : 4,
            "6" : 5,
            "7" : 6,
            "8" : 7,
            "9" : 8,
            "10" : 9,
            "11" : 10,
            "12" : 11,
            "13" : 12,
            "14" : 13,
        }
        # white-list
        self.white_list = [1, 2, 3, 4, 5, 6]
        self.assigned_distances : dict = {}
        self.white_list = []

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
        # time after which nodes get disconnected due to inactivity
        self.inactive_threshold = 1000*60*60*26
        # number of packets since last connection check
        self.num_packets_received_connection_check = np.zeros((100))
        # number of packets since last JOIN
        self.num_packets_received_after_join = np.zeros((100))

        '''RECEIVE CHECK'''
        # if a receive check was carried out during this interval
        self.receive_check_complete = False
        # nr of DATA packets received in one interval
        self.num_packets_received_interval = np.zeros((100))
        # packets that were missing int he last interval
        self.missing_interval_packets = []
        # cleanup of all variables used in receive check
        self.receive_check_cleanup = False

        '''STATISTICS'''
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

        self.statistics : dict = {
            "num_rx_after_start" : {},
            "num_rx" : {},
            "num_rx_requested" : {},
        }

        '''SENDING PARAMS'''
        # packet id stuff
        self.next_packet_id = 0
        self.spreading_factor = spreading_f

        '''DB'''
        # write db file or not
        self.write_db = db

    def setup(self):
        super().setup()

        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_%i" % self.spreading_factor)
        self.node.get_transceiver().set_tx_power(14)

        self.last_join_check = self.node.get_time()

        self.received_join_requests_first_node = np.ones((100))*self.node_id

        # adjust timing
        self.last_interval_start += self.node.get_time()
        self.next_interval_start += self.node.get_time()
        self.last_interval_broadcast = self.next_interval_start - self.interval_broadcast

        self.command_center = command_center(self.appID, self.node_id, self, self.debugger)

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

    def update_loop(self):
        super().update_loop()

        if(self.node.get_transceiver().has_received()):
            # print(self.node.get_transceiver().rec_list)
            rx_packet = self.node.get_transceiver().get_received()
            self.receive(rx_packet)
        
        # Executed once at the start of each interval
        time = self.node.get_time()
        if(time > self.next_interval_start ):
            
            '''
            RESET VARIABLES
            Set up state for the beginning of the new interval
            '''
            self.last_interval_start = self.next_interval_start
            self.next_interval_start = self.last_interval_start + self.interval

            self.receive_check_complete = False
            self.receive_check_cleanup = False

            self.debugger.log("---> START interval: %s" % (datetime.fromtimestamp(int(self.node.get_time()/1000)).strftime("%H:%M:%S")), 1)
            self.debugger.log("next interval: %s (%i)" % (datetime.fromtimestamp(int(self.next_interval_start/1000)).strftime("%H:%M:%S"), self.next_interval_start), 1)

            self.interval_count += 1
            
            if(self.successfully_started):
                refactor_network = False
                removed_idx = 0
                for i in range(self.num_connected_nodes):
                    # self.node_interval_ack[i] and 
                    # this prevents removal of last node because this node was sent an SET_INTERVAL packet because the network was refactored before
                    if(self.node_sending_status[i] and self.get_time() - self.last_connection[i] > self.inactive_threshold):
                        refactor_network = True
                        removed_idx = i
                        break

                if(refactor_network):
                    self.debugger.log("Removing node %s because of inactivity" % (self.node_ids[removed_idx]), 2)
                    # move last node to index of removed node if nde is not last in list
                    # this way only one SET_INTERVAL COMMAND is required
                    self.remove_node(self.node_ids[removed_idx])

            if(self.interval_count % self.interval_resync_after == 0):
                self.debugger.log("  RESYNCING INTERVAL DATA!", 1)
                # queue resync interval command
                self.command_center.register_command(resync_interval_command(0) )

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
            self.debugger.log("-> num connected nodes:   %i" % self.num_connected_nodes, 1)
            self.debugger.log("-> successfully started:  %s" % self.successfully_started, 1)
            self.debugger.log("-> network running:       %s" % self.network_running, 1)
            self.debugger.log("-> nodes sending:         %s" % self.nodes_started_sending, 1)
            self.debugger.log("-> all nodes sending:     %s" % self.all_nodes_sending, 1)
            self.debugger.log("-> nodes sleeping:        %s" % self.nodes_sleeping, 1)
            self.debugger.log("-> new nodes:             %s" % self.new_nodes_to_join, 1)

        ''' 
        JOIN REQUESTS
        handle all join requests that were received in the last interval
        '''
        if(self.node.get_time() - self.last_join_check > self.interval_join_check):
            self.debugger.log("  JOIN CHECK:", 2 if (self.num_empty_join_intervals < 4 or self.num_received_join_requests > 0) else 4)
            self.debugger.log("    received %i join requests" % self.num_received_join_requests, 2 if (self.num_empty_join_intervals < 4 or self.num_received_join_requests > 0) else 4)

            # if the nodes started sending the JOIN requests are scheduled to avoid
            # the sending interval
            # when the nodes are sleeping they are only handled once every interval
            if(self.nodes_started_sending):
                if(self.nodes_sleeping):
                    self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
                else:
                    self.last_join_check += self.interval_join_check
                    if(self.last_join_check > self.next_interval_start - self.interval_join_check - 30*1000 and self.last_join_check < self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width):
                        self.debugger.log("    Setting JOIN-CHECK to end of send-interval", 2)
                        self.last_join_check = self.next_interval_start - self.interval_join_check + self.num_connected_nodes*self.interval_slot_width
            else:
                self.last_join_check += self.interval_join_check

            node_to_join = None
            node_to_join_dist = 1
            node_to_join_first_node = self.node_id
            
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
                
                self.num_empty_join_intervals = 0
                self.new_nodes_to_join = True
                self.all_nodes_sending = False
                self.network_running = False

                node_to_join = self.received_join_requests[idx]
                node_to_join_first_node = self.received_join_requests_first_node[idx]

                if(node_to_join in self.node_ids):
                    node_to_join_dist = self.node_distances[self.node_ids.index(self.received_join_requests[idx])]
                elif(not node_to_join_first_node == self.node_id):
                    if(("%i" % node_to_join) in self.assigned_distances):
                        node_to_join_dist = self.assigned_distances.get("%i" % node_to_join)
                    else:
                        node_to_join_dist = self.node_distances[self.node_ids.index(int(node_to_join_first_node))] + 1

                # update connected node parameters
                # and
                # send the join requests
                if(not node_to_join in self.node_ids):
                    self.num_connected_nodes += 1
                    self.first_connection[self.num_connected_nodes-1] = self.node.get_time()
                    self.node_ids.append(int(node_to_join))
                    self.node_battery_level.append(-1)
                    # self.node_distances.append(nodes_to_join_dist[n])
                    self.node_distances.append(node_to_join_dist)
                    self.node_of_first_contact.append(node_to_join_first_node)
                    self.node_sending_status.append(False)
                    self.node_sleeping_status.append(False)
                    self.node_wanted_sleeping_status.append(False)
                    # not accepted interval
                    self.node_interval_ack.append(False)
                    self.node_interval_sent.append(False)

                    '''STATISTICS'''
                    self.statistics.get("num_rx_after_start").update( { str(int(node_to_join)) : 0} )
                    self.statistics.get("num_rx_requested").update( { str(int(node_to_join)) : 0} )

                else:
                    self.debugger.log("    Node %i: rejoining" % node_to_join, 1)
                    idx = self.node_ids.index(node_to_join)
                    self.node_interval_sent[idx] = False
                    self.node_interval_ack[idx] = False
                    self.node_sending_status[idx] = False
                    self.node_sleeping_status[idx] = False
                    self.num_packets_received_after_join[idx] = 0

                self.command_center.register_command(ack_join_command(
                        node_to_join,
                        node_to_join_dist,
                        self.node_id
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
            
            if(self.node.get_time() - self.last_interval_broadcast > self.interval_broadcast and self.next_interval_start - self.node.get_time() > self.num_connected_nodes*self.interval_slot_width):
                self.debugger.log("  INTERVAL-CHECK", 2)
                # if the nodes started sending the JOIN requests are scheduled to avoid
                # the sending interval
                # when the nodes are sleeping they are only handled once every interval
                if(self.nodes_started_sending):
                    if(self.nodes_sleeping):
                        self.last_interval_broadcast = self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width
                    else:
                        self.last_interval_broadcast += self.interval_broadcast
                        if(self.last_interval_broadcast > self.next_interval_start - self.last_interval_broadcast - 30*1000 and self.last_interval_broadcast < self.next_interval_start - self.interval_broadcast + self.num_connected_nodes*self.interval_slot_width):
                            self.debugger.log("    Setting INTERVAL-CHECK to end of send-interval", 2)
                            self.last_interval_broadcast = self.next_interval_start - self.last_interval_broadcast + self.num_connected_nodes*self.interval_slot_width
                        elif(self.last_interval_broadcast < self.get_time() - 1000):
                            self.debugger.log("    Resetting INTERVAL-CHECK", 2)
                            self.last_interval_broadcast = self.get_time()
                else:
                    self.last_interval_broadcast += self.interval_broadcast

                sent_int = []
                for i in range(len(self.node_ids)):
                    # change required_new_empty_join to 0 after start
                    # then check here if node_id in received joins
                    # print("%s and %s" % (str(not self.node_interval_sent[i]), str(not self.node_ids[i] in self.nodes_joined_last_interval)) )
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

                if(len(sent_int) > 0): self.debugger.log("  Sending interval data to nodes %s" % str(sent_int), 2)

                # check if all have ACK
                all_reached = True
                for i in range(len(self.node_ids)):
                    if(not self.node_interval_ack[i]):
                        all_reached = False
                        break

                # update logic, all connected nodes have sent ACK
                if(all_reached):
                    self.debugger.log("  Central: All connected nodes have ACK the interval", 1)
                    self.nodes_started_sending = True
                    self.new_nodes_to_join = False
                    # reduce number of required empty join intervals for faster rejoining of nodes
                    self.required_num_emtpy_join = 1

                    if(not self.successfully_started):
                        self.debugger.log("  Sending first START_SENDING to nodes", 1)
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
                        self.debugger.log("  Sending START_SENDING to nodes", 1)
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
        if(self.nodes_started_sending and not self.receive_check_complete and self.last_interval_start + self.interval_slot_width*self.num_connected_nodes < self.node.get_time()):

            # check the apckets that were received in this interval and compare against the packets that should have been received
            # if packet is missing, queue REQUEST command
            if(self.successfully_started):
                self.debugger.log("  checking the received packets", 2)
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

                self.debugger.log(nodes, 2)
                self.debugger.log(rec_pkt, 2)

                for i in range(self.num_connected_nodes):
                    if(self.num_packets_received_interval[i] == 0 and self.node_sending_status[i]):
                        self.debugger.log("    Missing packet from node: %i" % self.node_ids[i], 2)
                        self.missing_interval_packets.append(self.node_ids[i])
                        self.num_not_received_on_first_try += 1

                self.receive_check_complete = True

                for i in range(len(self.missing_interval_packets)):
                    self.command_center.register_command(request_command(self.missing_interval_packets[i], retry_sending=True))

            # check if at least one data packet from all nodes has been received after they joined.
            # if so, the network was successfully (re-)started
            if(not self.successfully_started or (self.successfully_started and not self.network_running)):
                self.debugger.log("  checking the received packets after joining", 2)
                
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

                self.debugger.log(nodes, 2)
                self.debugger.log(rec_pkt, 2)

                if(all_sending):
                    if (not self.successfully_started):
                        self.debugger.log("  SUCCESSFULLY STARTED THE NETWORK", 1)
                        self.successfully_started = True
                        self.required_num_emtpy_join = 0
                        self.time_started = self.get_time()

                        '''STATISTICS'''
                        d1 = {}
                        d2 = {}
                        for i in range(self.num_connected_nodes):
                            d1.update({ str(self.node_ids[i]) : int(self.num_packets_received_after_join[i]) } )
                            d2.update({ str(self.node_ids[i]) : 0 } )

                        self.statistics.update( {"num_rx_before_start" : d1} )
                        self.statistics.update( {"num_rx_requested" : d2} )
                        self.statistics.update( {"start_interval" : self.interval_count} )
                    else:
                        self.debugger.log("  SUCCESSFULLY RESTARTED THE NETWORK", 1)
                        self.time_restarted = self.get_time()

                        for i in range(len(self.node_ids)):
                            if(not (self.node_wanted_sleeping_status[i] == self.node_sleeping_status[i]) ):
                                self.command_center.register_command(ack_command(
                                    0,
                                    Command_type.ENABLE_SLEEP if self.node_wanted_sleeping_status[i] else Command_type.DISABLE_SLEEP,
                                    prio = 2
                                ))
                    
                    self.network_running = True
                    # update timing parameters for the JOIN and INTERVAL_BROPADCAST routines
                    # they are now executed once at the beginning of each interval
                elif( not self.successfully_started):
                    self.debugger.log("  Sending START_SENDING to nodes", 3)
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
        if(self.successfully_started and self.receive_check_complete and not self.receive_check_cleanup and self.last_interval_start + self.interval_slot_width*self.num_connected_nodes + self.interval_active_extension < self.node.get_time()):
            
            self.debugger.log("cleaning up receive-check")
            self.num_packets_received_interval = np.zeros((100))
            self.receive_check_cleanup = True
            self.missing_interval_packets = []
            self.num_packets_received_interval = np.zeros((100))
            self.debugger.log("<--- END of active part of interval")

        '''
        COMMAND CENTER
        '''
        # if(self.nodes_started_sending):
        self.command_center.update()

    # get next free packet id
    # counting up until 255 then return to 0
    # should be enouh to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    def receive(self, rx_packet : packet_dist) -> None:

        if(rx_packet.appID == self.appID):
            if(rx_packet.target == self.node_id or rx_packet.target == 0):
                
                # add to local storage
                self.pack_list.append(rx_packet)

                # check whitelist
                if(len(self.white_list) > 0 and not ( rx_packet.sender in self.white_list) ):
                    self.debugger.log("  not handling packet from %i because not in white-list" % rx_packet.sender, 3)
                
                # handle packet
                elif(self.check_multiple_packet(rx_packet)):

                    if(rx_packet.origin in self.node_ids):
                        idx = self.node_ids.index(rx_packet.origin)
                        self.last_connection[idx] = self.node.get_time()

                    if(rx_packet.payload_type == Payload_type.DATA):

                        self.debugger.log("  %s from node %i (pid=%i) (last sender=%i)" % (str(rx_packet.payload_type), rx_packet.origin, rx_packet.packet_id, rx_packet.sender ), 2)

                        # update link quality statistics
                        if(rx_packet.origin in self.node_ids):
                            idx = self.node_ids.index(rx_packet.origin)
                        
                            self.num_packets_received[idx] += 1
                            self.num_packets_received_connection_check[idx] += 1
                            self.num_packets_received_interval[idx] += 1
                            self.num_packets_received_after_join[idx] += 1

                            # update current battery level
                            self.node_battery_level[idx] = rx_packet.payload[1]

                            self.store_packet(rx_packet)
                        else:
                            self.debugger.log("ERROR: Sender not connected to this central station", 1)

                    elif(rx_packet.payload_type == Payload_type.JOIN):
                        self.debugger.log("  receiving join request from node with ID: %i with RSSI:%i" % (rx_packet.origin, rx_packet.rssi), 3)  
                        
                        self.received_join_requests[self.num_received_join_requests] = rx_packet.origin

                        # if packet has not been relayed
                        # payload of packet (=RSSI of first relay) is 0
                        if(rx_packet.payload[0] == 0):
                            self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.rssi
                            self.received_join_requests_first_node[self.num_received_join_requests] = self.node_id
                        else:
                            self.received_join_requests_rssi[self.num_received_join_requests] = rx_packet.payload[0]
                            self.received_join_requests_first_node[self.num_received_join_requests] = rx_packet.payload[1]

                        # add id to list if not already received
                        if(not rx_packet.origin in self.nodes_joined_last_interval):
                            self.nodes_joined_last_interval.append(rx_packet.origin)

                        self.command_center.remove_commands_for_node(rx_packet.origin, [Command_type.RESET, Command_type.JOIN_ACK])

                        self.num_received_join_requests += 1 

                        # reset sending status if node is rejoining
                        if(rx_packet.origin in self.node_ids):
                            idx = self.node_ids.index(rx_packet.origin)
                            self.node_sending_status[idx] = False

                    elif(rx_packet.payload_type is Payload_type.ACK):
                        self.debugger.log("  receiving ACK from node %i" % rx_packet.origin, 2)
                        idx = self.node_ids.index(rx_packet.origin)
                        self.node_interval_ack[idx] = True

                    # handle at command center
                    self.command_center.handle_packet(rx_packet)      
                else:
                    self.debugger.log("  Central: not handling packet %s from node %i because it was received multiple times (last sender=%i)" % (str(rx_packet.payload_type), rx_packet.origin, rx_packet.sender), 4)
            else:
                if(rx_packet.origin == self.node_id):
                    self.debugger.log("  Central: not handling packet %s because I sent it (last sender=%i)" % (str(rx_packet.payload_type), rx_packet.sender), 4)
                else:
                    self.debugger.log("  Central: not handling packet %s from node %i because of wrong target (last sender=%i)" % (str(rx_packet.payload_type), rx_packet.origin, rx_packet.sender), 3)
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
            # self.node.debugger.log("Node %s: not handling packet %s from node %i because it was received multiple times" % (self.node.name, str(rx_packet.payload_type)[13:], rx_packet.origin), 3)

        if(num_blocks > 0):
            return False
        else:
            self.last_packet_relay.append(self.node.get_time())
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

    def get_time(self) -> int:
        return self.node.get_time()

    def store_packet(self, rx_packet):

        if(rx_packet.origin in self.missing_interval_packets):
            self.debugger.log("    Received REQUESTED packet: %s" % str(rx_packet.debug_name), 2)
            self.statistics.get("num_rx_requested").update( { str(int(rx_packet.origin)) : self.statistics.get("num_rx_requested").get(str(int(rx_packet.origin))) + 1 } )
          
        # keep track of all received packets after the network was successfully started
        # ans also REQUEST packets are sent out
        if(self.successfully_started):
            self.num_rx_after_start += 1
            self.statistics.get("num_rx_after_start").update( { str(int(rx_packet.origin)) : self.statistics.get("num_rx_after_start").get(str(int(rx_packet.origin))) + 1 } )
          
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
            "interval" : self.interval,
            "artificial_blocks" : self.artificial_blocks,
            "handler" : type(self.packetHandler),
            "spread" : self.spreading_factor
        }

    @classmethod
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("store"),
            d.get("interval"),
            d.get("handler").from_dict(d),
            d.get("artificial_blocks"),
            d.get("spread") if "spread" in d else 10
        )
        return instance

    def __str__(self) -> str:
        return "%s(SF=%i)     with handler: %s" % (str(type(self)).split(".")[-1][:-2].rjust(25), self.spreading_factor, str(type(self.packetHandler)).split(".")[-1][:-2].rjust(20) )