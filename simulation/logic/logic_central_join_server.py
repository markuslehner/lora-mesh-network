from logic.handler_flooding import handler_flooding
from hw.packet import Payload_type, Command_type, Packet_type, lora_packet, packet_flooding
from logic.logic_central import logic_central
from logic.server import server

import numpy as np
import datetime
import random

class logic_central_pid_server(logic_central):

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