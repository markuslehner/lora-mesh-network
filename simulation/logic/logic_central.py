from logic.logic import logic_node_lora
from hw.packet import packet, Payload_type, Command_type, Packet_type
from typing import List
from logic.server import server

class logic_central(logic_node_lora):

    def __init__(self, appID : int, node_id : int, handler, spreading_f : int = 7) -> None:
        super().__init__(appID, node_id, handler, spreading_f)

    def setup(self):
        super().setup()
        self.server : server = self.node.transceiver.world.get_server(self.appID)
        self.server.register_gateway(self)

    def handle_server_request(self, rx_packet : packet, delay : int = 0):
        self.debugger.log("Handling server request: %s" % str(rx_packet), 5)
        self.queue_packet(rx_packet, delay)

    def update_loop(self): 
        super().update_loop()