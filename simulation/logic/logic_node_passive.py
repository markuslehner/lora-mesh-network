from logic.logic import logic_node_lora
from hw.packet import Payload_type, Command_type, packet_flooding
from logic.handler_flooding_basic import handler_flooding_basic
from sim.utils import get_air_time

import random

class logic_node_passive(logic_node_lora):

    def __init__(self, appID, node_id, send_interval, time_offset=None, handler=handler_flooding_basic(), spreading_f : int = 10) -> None:
        super().__init__(appID, node_id, handler, spreading_f)

        self.spreading_factor = spreading_f 
        self.send_interval = send_interval
        self.time_set_cooldown = 20000
        self.last_time_set = 0

        if(time_offset is None):
            self.last_send_time = random.randint(0, 20000)
            self.start_time_offset = self.last_send_time
        else:
            self.last_send_time = time_offset
            self.start_time_offset = time_offset

    def register(self, node):
        self.node = node

    def set_time_offset(self, time):
        self.last_send_time = time

    def get_interval(self):
        return self.send_interval

    def setup(self):
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_%i" % self.spreading_factor)
        self.node.get_transceiver().set_tx_power(14)

        self.packetHandler.register(self.node)

    def update_loop(self):
        super().update_loop()

        if(self.chapter == 0):
            if(self.node.get_transceiver().has_received()):
                rx_packet = self.node.get_transceiver().get_received()

                # check if its the same network
                if(rx_packet.appID == self.appID):
                    if(rx_packet.target == self.node_id):
                        # handle payload
                        # set display ...
                        self.debugger.log("delaying interval @ node %s by %i" % (self.node.name, rx_packet.payload[1]), 1)
                        if(rx_packet.payload_type == Payload_type.COMMAND):
                            if(rx_packet.payload[0] == Command_type.DELAY_INTERVAL):
                                self.last_send_time += rx_packet.payload[1]
                    else:
                        if(rx_packet.payload_type == Payload_type.TIME_SYNC):
                            # cooldown, to avoid setting the time many times in a row
                            if(self.node.get_time() - self.last_time_set > self.time_set_cooldown):
                                # no correction of air time
                                # self.last_send_time += rx_packet.payload - self.node.time
                                # self.node.set_time(rx_packet.payload)

                                # estimate transmission time and correct received time
                                est_time = rx_packet.payload + (rx_packet.num_hops * get_air_time(rx_packet.frequency, rx_packet.modulation, rx_packet.bandwidth, rx_packet.get_length()))
                                self.last_send_time += est_time - self.node.time
                                self.update_time(est_time)
                                self.last_time_set = self.node.get_time()
                                
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
                        debug_name=("%s_%s" % (self.node.name, str(self.send_cnt))) 
                    )
                )

            self.node.wait(10)
        else:
            self.node.wait(10)

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

    def __str__(self) -> str:
        return "%s (off=%i)    with handler: %s" % (str(type(self)).split(".")[-1][:-2].rjust(25), self.start_time_offset, str(type(self.packetHandler)).split(".")[-1][:-2].rjust(20) )