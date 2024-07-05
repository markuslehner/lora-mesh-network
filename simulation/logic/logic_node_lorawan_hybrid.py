from logic.logic import logic_node_lora
from hw.packet import Payload_type, lorawan_packet, Packet_type, LoRaWAN_type, Command_type, lora_packet

import random

class logic_node_lorawan_hybrid(logic_node_lora):

    def __init__(self, appID : int, node_id : int, send_interval : int, NwkKey : int, time_offset : int = None, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, None, spreading_factor=spreading_f)
        
        self.NwkKey : int = NwkKey
        self.send_interval : int = send_interval

        self.connected : bool = False
        self.last_connection_retry : int = -random.randint(0, 47000)
        self.connection_retry : int = 47000
        self.max_retries : int = 6
        self.retry_counter : int = 0

        self.next_sleep_time : int = 0
        self.go_to_sleep = False
        self.sleeping_enabled : bool = False

        # if has dependent nodes
        self.dependent_nodes = []
        self.node_spacing : int = 560

        self.is_dependent = False
        self.relayer_node : int = 0

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
    

    def handle_packet_lorawan(self, rx_packet : lorawan_packet):
        if(self.connected):
            if(rx_packet.appID == self.appID):
                if(rx_packet.target == 0):
                    if(rx_packet.payload_type == LoRaWAN_type.UNCONFIRMED_DATA_DOWN):
                        self.debugger.log("%s: receiving packet from GW%i" % (self.node.name, rx_packet.origin), 3)
                        if(rx_packet.payload[0] == Payload_type.COMMAND):
                            if(rx_packet.payload[1] == Command_type.ENABLE_SLEEP):
                                self.debugger.log("%s: receiving ENABLE_SLEEP request from GW%i" % (self.node.name, rx_packet.origin), 2)
                                self.sleeping_enabled = True
                                self.next_sleep_time = self.node.get_time() + self.send_interval
                            elif(rx_packet.payload[1] == Command_type.DISABLE_SLEEP):
                                self.debugger.log("%s: receiving DISABLE_SLEEP request from GW%i" % (self.node.name, rx_packet.origin), 2)
                                self.sleeping_enabled = False
                            
                            if(len(self.dependent_nodes) > 0):
                                self.debugger.log("%s: relaying COMMAND to dependent nodes" % (self.node.name), 2)
                                self.node.transceiver.send(
                                    lora_packet(
                                        self.appID,
                                        self.node_id,
                                        0,
                                        Payload_type.COMMAND,
                                        rx_packet.payload[1:]
                                    )
                                )
                elif(rx_packet.target == self.node_id):
                    if(rx_packet.payload_type == LoRaWAN_type.UNCONFIRMED_DATA_DOWN):
                        self.debugger.log("%s: receiving packet from GW%i" % (self.node.name, rx_packet.origin), 3)
                        if rx_packet.payload[0] == Payload_type.JOIN_ACK:
                            self.debugger.log("%s: RELAY JOIN for node %i successful" % (self.node.name, rx_packet.payload[1]), 1)
                            if(rx_packet.payload[1] not in self.dependent_nodes):
                                self.dependent_nodes.append(rx_packet.payload[1])
                            self.node.get_transceiver().send(
                                lora_packet(
                                    self.appID,
                                    self.node_id,
                                    rx_packet.payload[1],
                                    Payload_type.JOIN_ACK,
                                    [self.send_interval, self.send_interval - (self.node.get_time() - self.last_send_time) + len(self.dependent_nodes) * self.node_spacing],
                                )
                            )

        else:
            if(rx_packet.appID == self.appID):
                if(rx_packet.target == self.node_id):
                    if(rx_packet.payload_type == LoRaWAN_type.JOIN_ACCEPT):
                        self.debugger.log("%s: successfully registered with network" % self.node.name, 1)
                        self.connected = True
                        # set last_send_time to start first transmission after the specified offset + relay_block_time
                        self.last_send_time = self.node.get_time() - self.send_interval + 3000


    def handle_packet_lora(self, rx_packet : lora_packet):
        self.debugger.log("%s: receiving LORA packet %s" % (self.node.name, str(rx_packet)), 3)
        if self.connected:
            if(rx_packet.appID == self.appID):
                if (rx_packet.target == self.node_id):
                    if rx_packet.payload_type == Payload_type.DATA_RELAY:
                        self.debugger.log("%s: relaying data from node %i" % (self.node.name, rx_packet.origin), 2)
                        self.node.get_transceiver().send(
                            lorawan_packet(
                                self.appID,
                                self.node_id,
                                255,
                                LoRaWAN_type.UNCONFIRMED_DATA_UP,
                                [Payload_type.DATA_RELAY, rx_packet.origin, rx_packet.payload[0]],
                                packet_id = self.get_packet_id(),
                                debug_name=rx_packet.debug_name,
                                origin=rx_packet.origin
                            )
                        )
                elif (rx_packet.target == 255):
                    if(rx_packet.payload_type == Payload_type.JOIN):
                        self.debugger.log("%s: receiving RELAY JOIN request from node%i" % (self.node.name, rx_packet.origin), 2)
                        self.node.get_transceiver().send(
                            lorawan_packet(
                                self.appID,
                                self.node_id,
                                255,
                                LoRaWAN_type.UNCONFIRMED_DATA_UP,
                                [Payload_type.JOIN, rx_packet.origin, rx_packet.payload[0], rx_packet.payload[1]],
                                packet_id = self.get_packet_id()
                            )
                        )

                elif(rx_packet.target == 0):
                    if(rx_packet.payload_type == Payload_type.COMMAND):
                        if(rx_packet.payload[0] == Command_type.ENABLE_SLEEP):
                            self.debugger.log("%s: receiving ENABLE_SLEEP request from node %i" % (self.node.name, rx_packet.origin), 2)
                            self.sleeping_enabled = True
                            self.next_sleep_time = self.node.get_time() + self.send_interval
                        elif(rx_packet.payload[0] == Command_type.DISABLE_SLEEP):
                            self.debugger.log("%s: receiving DISABLE_SLEEP request from node %i" % (self.node.name, rx_packet.origin), 2)
                            self.sleeping_enabled = False

        else:
            if(rx_packet.appID == self.appID):
                if(rx_packet.target == self.node_id):
                  if rx_packet.payload_type == Payload_type.JOIN_ACK and self.retry_counter >= self.max_retries:
                        self.debugger.log("%s: successfully registered with network (DEPENDENT)" % self.node.name, 1)
                        self.connected = True
                        self.is_dependent = True
                        self.relayer_node = rx_packet.origin
                        self.send_interval = rx_packet.payload[0]
                        self.last_send_time = self.node.get_time() - self.send_interval + rx_packet.payload[1]


    def update_loop(self):

        super().update_loop()

        if(self.chapter == 0):
            if(self.node.get_transceiver().has_received()):
                rx_packet : lorawan_packet = self.node.get_transceiver().get_received()
                if(rx_packet.packet_type == Packet_type.LORAWAN):
                    self.handle_packet_lorawan(rx_packet)
                elif(rx_packet.packet_type == Packet_type.LORA):
                    self.handle_packet_lora(rx_packet)

            if(self.connected):
                if(self.node.get_time() - self.last_send_time > self.send_interval):
                    self.last_send_time = self.node.get_time()
                    self.send_cnt += 1
                    self.next_sleep_time = self.node.get_time() + 500 + len(self.dependent_nodes) * self.node_spacing
                    self.go_to_sleep = self.sleeping_enabled

                    self.debugger.log("%s: sending data (dependent:%s)" % (self.node.name, str(self.is_dependent)), 2)

                    if(self.is_dependent):
                        self.node.get_transceiver().send(
                            lora_packet(
                                self.appID,
                                self.node_id,
                                self.relayer_node,
                                Payload_type.DATA_RELAY,
                                [self.node.sensor.get_value()],
                                debug_name=("%s_%s" % (self.node.name, str(self.send_cnt))) 
                            )
                        )
                    else:
                        self.node.get_transceiver().send(
                            lorawan_packet(
                                self.appID,
                                self.node_id,
                                255,
                                LoRaWAN_type.UNCONFIRMED_DATA_UP,
                                [Payload_type.DATA, self.node_id, self.node.sensor.get_value()],
                                packet_id= self.get_packet_id(),
                                debug_name=("%s_%s" % (self.node.name, str(self.send_cnt))) 
                            )
                        )

                if(self.go_to_sleep and self.next_sleep_time < self.node.get_time()):
                    self.node.get_transceiver().start_sleep()
                    self.chapter = 1
                    self.node.sleep(self.last_send_time - self.node.get_time() + self.send_interval - 5000)
                    self.clear_packet_queue()
                    self.debugger.log("%s: starting to sleep" % (self.node.name), 2)

            else:
                if(self.node.get_time() - self.last_connection_retry > self.connection_retry):
                    if(self.retry_counter < self.max_retries):
                        # print("%s: sending JOIN request" % self.node.name)
                        self.last_connection_retry = self.node.get_time() + random.randint(0, 15000)
                        self.node.get_transceiver().send(
                                lorawan_packet(
                                    self.appID,
                                    self.node_id,
                                    255,
                                    LoRaWAN_type.JOIN_REQUEST,
                                    [self.NwkKey, self.send_interval],
                                    packet_id= self.get_packet_id()
                                )
                            )
                        self.retry_counter += 1
                    else:
                        self.debugger.log("%s: Sending RELAY JOIN" % self.node.name, 2)
                        self.last_connection_retry = self.node.get_time() + random.randint(0, 15000)
                        self.node.get_transceiver().send(
                                lora_packet(
                                    self.appID,
                                    self.node_id,
                                    255,
                                    Payload_type.JOIN,
                                    [self.NwkKey, self.send_interval]
                                )
                            )
                        self.retry_counter += 1


            self.node.wait(20)
        elif(self.chapter == 1):
            self.debugger.log("%s: waking up" % (self.node.name), 2)
            self.node.get_transceiver().stop_sleep()
            self.chapter = 0        
            self.go_to_sleep = False
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
