from logic.logic import logic_node
from hw.packet import lorawan_packet, Packet_type, LoRaWAN_type
from logic.handler_flooding_pid import handler_flooding_pid
from sim import debugger, world

import random

class logic_node_lorawan(logic_node):

    def __init__(self, appID : int, node_id : int, send_interval : int, NwkKey : int, time_offset : int=None) -> None:
        super().__init__(appID, node_id)
        
        self.NwkKey : int = NwkKey
        self.send_interval : int = send_interval

        self.connected : bool = False
        self.last_connection_retry : int = -random.randint(0, 67000)
        self.connection_retry : int = 67000

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
                    rx_packet : lorawan_packet = self.node.get_transceiver().get_received()
                    if(rx_packet.packet_type == Packet_type.LORAWAN):
                        if(rx_packet.target == self.node_id):
                            # handle payload
                            pass
                            
                if(self.node.get_time() - self.last_send_time > self.send_interval):
                    self.last_send_time = self.node.get_time()
                    self.send_cnt += 1
                    self.node.get_transceiver().send(
                        lorawan_packet(
                            self.appID,
                            self.node_id,
                            0,
                            LoRaWAN_type.UNCONFIRMED_DATA_UP,
                            [self.node.sensor.get_value()],
                            packet_id= self.get_packet_id(),
                            debug_name=("%s_%s" % (self.node.name, str(self.send_cnt))) 
                        )
                    )

                if(self.last_send_time < self.node.get_time()):
                    last_sleep = self.next_sleep_interval
                    self.next_sleep_interval = self.node.get_time() + self.send_interval

                    self.node.get_transceiver().start_sleep()
                    self.chapter = 1
                    self.node.sleep(self.last_send_time - self.node.get_time() + self.send_interval - 5000)
                    self.clear_packet_queue()
                    self.debugger.log("%s: starting to sleep" % (self.node.name), 3)

            else:
                if(self.node.get_transceiver().has_received()):
                    rx_packet : lorawan_packet = self.node.get_transceiver().get_received()
                    if(rx_packet.packet_type == Packet_type.LORAWAN):
                        # check if its the same network
                        if(rx_packet.appID == self.appID):
                            if(rx_packet.target == self.node_id):
                                # handle payload
                                # set display ...
                                if(rx_packet.payload_type == LoRaWAN_type.JOIN_ACCEPT):
                                    self.debugger.log("%s: successfully registered with network" % self.node.name, 1)
                                    self.connected = True
                                    # set last_send_time to start first transmission after the specified offset + relay_block_time
                                    self.last_send_time = self.node.get_time() - self.send_interval + 30000 + self.start_time_offset

                elif(self.node.get_time() - self.last_connection_retry > self.connection_retry):
                    # print("%s: sending JOIN request" % self.node.name)
                    self.last_connection_retry = self.node.get_time() + random.randint(0, 15000)
                    self.node.get_transceiver().send(
                            lorawan_packet(
                                self.appID,
                                self.node_id,
                                0,
                                LoRaWAN_type.JOIN_REQUEST,
                                self.send_interval,
                                10,
                                packet_id= self.get_packet_id()
                            )
                        )

            self.node.wait(20)
        else:
            self.node.wait(20)


    def to_dict(self) -> dict:
        d =  super().to_dict()
        d.update({"send_interval" : self.send_interval})
        d.update({"time_offset" : self.start_time_offset})
        d.update({"NwkKey" : self.NwkKey})
        return d

    @classmethod    
    def from_dict(cls, d):
        instance = cls(
            d.get("appID"),
            d.get("node_id"),
            d.get("send_interval"),
            d.get("NwkKey"),
            d.get("time_offset")
        )
        return instance
