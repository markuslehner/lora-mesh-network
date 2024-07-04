from hw.packet import Packet_type, lora_packet
from logic.logic import logic_gateway

import numpy as np
import datetime
import random

class logic_central_pid_server(logic_gateway):

    def __init__(self, appID : int, node_id : int, handler, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, handler, spreading_f)


    def update_loop(self):
        super().update_loop()

        if(self.chapter == 0):
            if(self.node.get_transceiver().has_received()):
                rx_packet : lora_packet = self.node.get_transceiver().get_received()
                if(rx_packet.packet_type == Packet_type.LORA):
                    self.server.handle_packet(rx_packet) 
        else:
            self.node.wait(10)