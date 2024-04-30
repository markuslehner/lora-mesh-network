from logic.logic import logic, logic_node
from hw.packet import Payload_type, Command_type 
from hw.packet_dist import packet_dist
from logic.handler_flooding import handler_flooding
from logic.handler_dist_pid import handler_dist_pid
from sim import world

import random

class logic_node_lmn(logic_node):

    def __init__(self, appID : int, node_id : int, handler=handler_dist_pid(), blocks : list[int] = [], spreading_f : int = 10) -> None:
        super().__init__(appID, node_id, handler)

        self.artificial_blocks = blocks
        self.spreading_factor = spreading_f

        # id of central node
        self.central_id = 0

        # interval in which to send DATA to central
        self.send_interval = 1000*10

        # indication if connected to network
        self.connected = False
        # indication if sending was activated
        self.sending_active = False
        # indication if sleeping was activated
        self.sleeping_active = False

        # simulate, that not all nodes start at the same time and send a JOIN request
        self.last_connection_retry = random.randint(0, 15000)
        self.connection_retry = 15000

        self.time_set_cooldown = 15000
        self.last_time_set = 0

        self.delay_interval_cooldown = 15000
        self.last_delay = 0

        self.interval_set_cooldown = 15000
        self.last_interval_set = 0

        self.request_answer_cooldown = 15000
        self.last_request_answer = 0

        self.last_send_time = 0

        # distance from central node
        self.distance = 127
        # packet id counter
        self.packet_id = 0

        # sleep interval data
        # time offset between interval start and transmission of own DATA
        self.interval_offset = 0
        # time to stay active during interval
        self.interval_active_time = 0
        # if received interval
        self.received_interval = False
        # next start of sleep interval
        self.next_sleep_interval = 0
        # buffer for the sleeping cycle so the node wakes up a bit earlier than received from central
        self.wakeup_bumper = 1000*10

    def register(self, node):
        self.node = node

    def set_time_offset(self, time):
        self.last_send_time = time

    def get_interval(self):
        return self.send_interval

    # get next free packet id
    # counting up until 255 then return to 0
    # should be enouh to differentiate the packets in the network
    def get_packet_id(self) -> int:
        last = self.packet_id
        self.packet_id += 1
        if(self.packet_id > 255):
            self.packet_id = 0

        return last

    def setup(self):
        # self.packetHandler = handler_flooding()
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_%i" % self.spreading_factor)
        self.node.get_transceiver().set_tx_power(14)

        self.packetHandler.register(self.node)

    def update_loop(self):

        super().update_loop()

        if(self.chapter == 0):

            if(self.node.get_transceiver().has_received()):
                rx_packet = self.node.get_transceiver().get_received()

                if(rx_packet.sender in self.artificial_blocks):
                    self.debugger.log("%s: not handling packet from %i because of artificial block" % (self.node.get_name(), rx_packet.sender), 2)
                else:
                    if(rx_packet.target == self.node_id):
                        self.handle_own_packet(rx_packet)
                    else:
                        self.handle_foreign_packet(rx_packet)

            if(self.connected):
                
                # send DATA to central
                # if active and at correct interval
                if(self.node.get_time() - self.last_send_time > self.send_interval):
                    self.last_send_time = self.node.get_time()
                    if(self.sending_active): 
                        self.send_cnt += 1
                        self.debugger.log("%s: sending DATA (p_id=%i)" % (self.node.name, self.packet_id), 3)
                        self.node.get_transceiver().send(
                            packet_dist(
                                self.appID,
                                self.node_id,
                                self.central_id,
                                8,
                                self.get_packet_id(),
                                self.distance,
                                True,
                                Payload_type.DATA,
                                [self.node.sensor.get_value(), 77],
                                debug_name=("%s_%i" % (self.node.name, self.send_cnt)) 
                            )
                        )
                       
                if(self.next_sleep_interval < self.node.get_time()):
                    last_sleep = self.next_sleep_interval
                    self.next_sleep_interval = self.node.get_time() + self.send_interval

                    if(self.sleeping_active):
                        self.node.get_transceiver().start_sleep()
                        self.chapter = 1
                        self.node.sleep(last_sleep - self.node.get_time() + self.send_interval - self.interval_active_time - self.wakeup_bumper)
                        self.clear_packet_queue()
                        self.debugger.log("%s: starting to sleep %s" % (self.node.name, self.sleeping_active), 3)
            else:
                if(self.node.get_time() - self.last_connection_retry > self.connection_retry):
                    # added random jitter to avoid 100% collision rate when nodes have same startup offset
                    self.last_connection_retry = self.node.get_time() + random.randint(-3000, 3000)
                    self.node.get_transceiver().send(
                            packet_dist(
                                self.appID,
                                self.node_id,
                                self.central_id,
                                10,
                                self.get_packet_id(),
                                self.distance,
                                True,
                                Payload_type.JOIN,
                                [0, 0]  # rssi, first network node distance
                            )
                        )

            self.node.wait(20)
        elif(self.chapter == 1):

            self.debugger.log("%s: waking up" % (self.node.name), 3)
            self.node.get_transceiver().stop_sleep()
            self.chapter = 0

            self.node.wait(20)
        else:
            self.node.wait(20)

    def handle_foreign_packet(self, rx_packet):

        if(self.connected):
            if(rx_packet.payload_type == Payload_type.TIME_SYNC):
                self.set_time(rx_packet)
            elif(rx_packet.payload_type == Payload_type.COMMAND):
                if(rx_packet.payload[0] == Command_type.START_SENDING):
                    if(not self.sending_active):
                        self.debugger.log("%s: Received START_SENDING" % (self.node.name), 2)

                    self.sending_active = True

                elif(rx_packet.payload[0] == Command_type.SET_INTERVAL):
                    if(self.received_interval):
                        # update interval data if active interval duration changes
                        # this happens when nodes join after this node has received its interval data
                        if(self.interval_active_time != rx_packet.payload[2]):
                            self.next_sleep_interval += rx_packet.payload[2] - self.interval_active_time 
                            self.debugger.log("%s: Moving interval active time by %i" % (self.node.name, rx_packet.payload[2] - self.interval_active_time), 2)
                            self.interval_active_time = rx_packet.payload[2]

                elif(rx_packet.payload[0] == Command_type.RESYNC_INTERVAL):
                    if(self.received_interval and self.node.get_time() - self.last_interval_set > self.interval_set_cooldown):
                        self.last_interval_set = self.node.get_time()

                        # estimate transmission delay
                        est_time_delay = (rx_packet.num_hops * world.get_air_time(rx_packet.frequency, rx_packet.modulation, rx_packet.bandwidth, rx_packet.get_length()))
                        est_time_delay += + ((rx_packet.num_hops-1) * self.packetHandler.relay_time/2) 
                        
                        # update own sending params
                        # central sent time until next interval start = payload[4]
                        # calculate the local time at which this happens
                        next_interval_start = self.node.get_time() + rx_packet.payload[1] - est_time_delay
                        self.debugger.log("%s: interval start= %i" % (self.node.name, next_interval_start), 3)
                        # set next sleeping interval
                        self.next_sleep_interval = next_interval_start + self.interval_active_time
                        self.last_send_time = next_interval_start + self.interval_offset

                elif(rx_packet.payload[0] == Command_type.ENABLE_SLEEP):
                    self.debugger.log("  %s: received command to ENABLE SLEEPING" % self.node.name, 2)
                    self.sleeping_active = True
                elif(rx_packet.payload[0] == Command_type.DISABLE_SLEEP):
                    self.sleeping_active = False

        self.packetHandler.handle_packet(rx_packet)

    def handle_own_packet(self, rx_packet : packet_dist):

        if(self.connected):
            # handle payload
            # set display ...
            if(rx_packet.payload_type == Payload_type.COMMAND):
                if(rx_packet.payload[0] == Command_type.DELAY_INTERVAL):
                    if(self.node.get_time() - self.last_delay > self.delay_interval_cooldown):
                        self.last_delay = self.node.get_time()
                        self.debugger.log("delaying interval @ node %s by %i" % (self.node.name, rx_packet.payload[1]), 1)
                        self.last_send_time += rx_packet.payload[1]

                elif(rx_packet.payload[0] == Command_type.SET_INTERVAL):
                    if(self.node.get_time() - self.last_interval_set > self.interval_set_cooldown):
                        self.last_interval_set = self.node.get_time()

                        # estimate transmission delay
                        est_time_delay = (rx_packet.num_hops * world.get_air_time(rx_packet.frequency, rx_packet.modulation, rx_packet.bandwidth, rx_packet.get_length()))
                        est_time_delay += ((rx_packet.num_hops-1) * self.packetHandler.relay_time/2) 

                        self.send_interval = rx_packet.payload[1]
                        self.interval_active_time = rx_packet.payload[2]
                        self.interval_offset = rx_packet.payload[3]
                        
                        # update own sending params
                        # central sent time until next interval start = payload[4]
                        # calsulate the local time at which tis happens
                        next_interval_start = self.node.get_time() + rx_packet.payload[4] - est_time_delay
                        self.debugger.log("%s: interval start= %i" % (self.node.name, next_interval_start),2 )
                        # set next sleeping interval
                        self.next_sleep_interval = next_interval_start + self.interval_active_time
                        self.last_send_time = next_interval_start + self.interval_offset - self.send_interval

                        self.sending_active = rx_packet.payload[5] > 0

                        # send ACK to central
                        self.queue_packet(
                            packet_dist(
                                self.appID,
                                self.node_id,
                                self.central_id,
                                10,
                                self.get_packet_id(),
                                self.distance,
                                True,
                                Payload_type.ACK,
                                rx_packet.packet_id
                            ),
                            4000
                        )

                        self.debugger.log("%s: successfully received interval data [int:%i, off:%i, active:%i, send:%s]" % (self.node.name, self.send_interval, self.interval_offset, self.interval_active_time, self.sending_active), 1)

                elif(rx_packet.payload[0] == Command_type.REQUEST):
                    if(self.node.get_time() - self.last_request_answer > self.request_answer_cooldown):
                        self.last_request_answer = self.node.get_time()

                        self.debugger.log("    %s: receiving REQUEST, sending DATA again" % (self.node.name), 2)

                        self.queue_packet(
                            packet_dist(
                                    self.appID,
                                    self.node_id,
                                    self.central_id,
                                    8,
                                    self.get_packet_id(),
                                    self.distance,
                                    True,
                                    Payload_type.DATA,
                                    [self.node.sensor.get_value(), 77],
                                    debug_name=("%s_%i" % (self.node.name, self.send_cnt)) 
                                ),
                                2500
                        )
                elif(rx_packet.payload[0] == Command_type.ENABLE_SLEEP):
                    # self.sleeping_active = True
                    pass
                elif(rx_packet.payload[0] == Command_type.DISABLE_SLEEP):
                    self.sleeping_active = False
        else:
            # JOIN ACK
            if(rx_packet.payload_type == Payload_type.JOIN_ACK):
                self.debugger.log("%s: successfully registered with base station %i at distance: %i" % (self.node.name, rx_packet.origin, rx_packet.payload[1]), 1)
                self.connected = True
                self.distance = rx_packet.payload[1]
                self.central_id = rx_packet.origin

    def set_time(self, rx_packet):
        # cooldown, to avoid setting the time many times in a row
        if(self.node.get_time() - self.last_time_set > self.time_set_cooldown):
            # no correction of air time
            # self.last_send_time += rx_packet.payload - self.node.time
            # self.node.set_time(rx_packet.payload)

            # estimate transmission time and correct received time
            est_time = rx_packet.payload + (rx_packet.num_hops * world.get_air_time(rx_packet.frequency, rx_packet.modulation, rx_packet.bandwidth, rx_packet.get_length()))

            # when using handler_flooding, relay time is random
            # max relay time/2 should be the expected value
            if(type(self.packetHandler) is handler_flooding or type(self.packetHandler) is handler_dist_pid):
                est_time += + ((rx_packet.num_hops-1) * self.packetHandler.relay_time/2) 

            self.update_time(est_time)
            # after update to use new time
            self.last_time_set = self.node.get_time()

    def update_time(self, new_time) -> None:

        self.last_send_time += new_time - self.node.get_time()
        if(type(self.packetHandler) is handler_flooding):
            self.packetHandler.update_time(new_time)
        # always call last, bevause is super the time is set and then no correction is possible
        # because node.time == time
        super().update_time(new_time)

    def reset(self):

        self.debugger.log("  %s: resetting logic" % self.node.name, 2)

         # indication if connected to network
        self.connected = False
        # indication if sending was activated
        self.sending_active = False
        # indication if sleeping was activated
        self.sleeping_active = False
        # distance from central node
        self.distance = 127
        # packet id counter
        self.packet_id = 0

        # sleep interval data
        # time offset between interval start and transmission of own DATA
        self.interval_offset = 0
        # time to stay active during interval
        self.interval_active_time = 0
        # if received interval
        self.received_interval = False
        # next start of sleep interval
        self.next_sleep_interval = 0

        # simulate, that not all nodes start at the same time and send a JOIN request
        self.last_connection_retry = self.node.get_time() - random.randint(0, 55000)
        self.last_time_set = 0
        self.last_delay = 0
        self.last_interval_set = 0
        self.last_request_answer = 0
        self.last_send_time = 0

    def to_dict(self) -> dict:
        d =  super().to_dict()
        d.update({"packet_handler" : type(self.packetHandler)})
        d.update({"artificial_blocks" : self.artificial_blocks})
        d.update({"spread" : self.spreading_factor})
        return d

    @classmethod    
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("packet_handler").from_dict(d),
            d.get("artificial_blocks"),
            d.get("spread") if "spread" in d else 10
        )
        return instance
        
    def __str__(self) -> str:
        return "%s(SF=%i)     with handler: %s" % (str(type(self)).split(".")[-1][:-2].rjust(25), self.spreading_factor, str(type(self.packetHandler)).split(".")[-1][:-2].rjust(20) )