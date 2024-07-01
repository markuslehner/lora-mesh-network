from logic.logic import logic_node
from hw.packet import packet, Payload_type, Packet_type

from typing import List


class logic_central_lora(logic_node):

    def __init__(self, appID : int = 0, node_ID : int = 0) -> None:
        super().__init__(appID, node_ID)

        # list of all packets received by this node
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 20000
        self.network_server = None

    def setup(self):
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_10")
        self.node.get_transceiver().set_tx_power(14)

        self.network_server = self.node.transceiver.world.get_server(self.appID)
        if(self.network_server is None):
            self.debugger.log("No server found for appID %i" % self.appID, 1)
        else:
            self.network_server.register(self)


    def update_loop(self): 
        super().update_loop()


    def receive(self, rx_packet) -> None:
        if(rx_packet.packet_type == Packet_type.LORAWAN):
            # check if its the same network
            if(rx_packet.appID == self.appID):
                if(rx_packet.target == self.node_id or rx_packet.target == 0):
                    self.network_server.handle_packet(rx_packet)