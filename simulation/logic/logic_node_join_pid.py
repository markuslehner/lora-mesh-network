from logic.logic import logic_node_lora
from hw.packet import lora_packet, Packet_type, Payload_type, Command_type, packet_flooding
from logic.handler_flooding_pid import handler_flooding_pid
from sim import debugger, world

import random

class logic_node_join_pid(logic_node_lora):

    def __init__(self, appID : int, node_id : int, send_interval : int, time_offset : int=None, handler=handler_flooding_pid()) -> None:
        super().__init__(appID, node_id, handler)
        self.send_interval = send_interval

        self.connected = False
        self.last_connection_retry = -random.randint(0, 67000)
        self.connection_retry = 67000

        self.time_set_cooldown = 20000
        self.last_time_set = 0

        self.delay_interval_cooldown = 20000
        self.last_delay = 0

        if(time_offset is None):
            self.last_send_time = random.randint(0, 20000)
            self.start_time_offset = self.last_send_time
        else:
            self.last_send_time = time_offset
            self.start_time_offset = time_offset

        # packet id counter
        self.next_packet_id = 0

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
        last = self.next_packet_id
        self.next_packet_id += 1
        if(self.next_packet_id > 255):
            self.next_packet_id = 0

        return last

    def setup(self):
        # self.packetHandler = handler_flooding()
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_1")
        self.node.get_transceiver().set_tx_power(20)

        self.packetHandler.register(self.node)

    def update_loop(self):

        super().update_loop()

        if(self.chapter == 0):

            if(self.connected):

                if(self.node.get_transceiver().has_received()):
                    rx_packet : lora_packet = self.node.get_transceiver().get_received()
                    if(rx_packet.packet_type == Packet_type.LORA):
                        if(rx_packet.target == self.node_id):
                            # handle payload
                            # set display ...
                            if(rx_packet.payload_type == Payload_type.COMMAND):
                                if(rx_packet.payload[0] == Command_type.DELAY_INTERVAL):
                                    if(self.node.get_time() - self.last_delay > self.delay_interval_cooldown):
                                        self.last_delay = self.node.get_time()
                                        self.debugger.log("delaying interval @ node %s by %i" % (self.node.name, rx_packet.payload[1]), 1)
                                        self.last_send_time += rx_packet.payload[1]
                        else:
                            if(rx_packet.payload_type == Payload_type.TIME_SYNC):
                                self.set_time(rx_packet)
                                    
                            self.packetHandler.handle_packet(rx_packet)

                if(self.node.get_time() - self.last_send_time > self.send_interval):
                    self.last_send_time = self.node.get_time()
                    self.send_cnt += 1
                    self.node.get_transceiver().send(
                        packet_flooding(
                            self.appID,
                            self.node_id,
                            0,
                            Payload_type.DATA,
                            self.node.sensor.get_value(),
                            5,
                            packet_id= self.get_packet_id(),
                            debug_name=("%s_%s" % (self.node.name, str(self.send_cnt))) 
                        )
                    )
            else:
                if(self.node.get_transceiver().has_received()):
                    rx_packet = self.node.get_transceiver().get_received()

                    # check if its the same network
                    if(rx_packet.appID == self.appID):
                        if(rx_packet.target == self.node_id):
                            # handle payload
                            # set display ...
                            if(rx_packet.payload_type == Payload_type.ACK):
                                self.debugger.log("%s: successfully registered with base station" % self.node.name, 1)
                                self.connected = True
                                # set last_send_time to start first transmission after the specified offset + relay_block_time
                                self.last_send_time = self.node.get_time() - self.send_interval + 30000 + self.start_time_offset

                            elif(rx_packet.payload_type == Payload_type.TIME_SYNC):
                                self.set_time(rx_packet)

                        else:
                            self.packetHandler.handle_packet(rx_packet)

                elif(self.node.get_time() - self.last_connection_retry > self.connection_retry):
                    # print("%s: sending JOIN request" % self.node.name)
                    self.last_connection_retry = self.node.get_time() + random.randint(0, 15000)
                    self.node.get_transceiver().send(
                            packet_flooding(
                                self.appID,
                                self.node_id,
                                0,
                                Payload_type.JOIN,
                                self.send_interval,
                                10,
                                packet_id= self.get_packet_id()
                            )
                        )

            self.node.wait(20)
        else:
            self.node.wait(20)

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
            if(type(self.packetHandler) is handler_flooding_pid):
                est_time += + ((rx_packet.num_hops-1) * self.packetHandler.relay_time/2) 

            self.update_time(est_time)
            # after update to use new time
            self.last_time_set = self.node.get_time()

    def update_time(self, new_time) -> None:

        self.last_send_time += new_time - self.node.get_time()
        if(type(self.packetHandler) is handler_flooding_pid):
            self.packetHandler.update_time(new_time)
        # always call last, bevause is super the time is set and then no correction is possible
        # because node.time == time
        super().update_time(new_time)



    def to_dict(self) -> dict:
        d =  super().to_dict()
        d.update({"send_interval" : self.send_interval})
        d.update({"time_offset" : self.start_time_offset})
        d.update({"packet_handler" : type(self.packetHandler)})
        return d

    @classmethod    
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("send_interval"),
            d.get("time_offset"),
            d.get("packet_handler").from_dict(d)
        )
        return instance
