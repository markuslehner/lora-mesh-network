from logic.handler_flooding_basic import handler_flooding_basic
from logic.logic import logic_central_lora
from logic.handler_flooding import handler_flooding
from hw.packet import Payload_type, Command_type, packet_flooding, packet
from typing import List

class logic_central_passive(logic_central_lora):

    def __init__(self, appID=0, node_id : int = 0) -> None:
        super().__init__(appID, node_id)

        # list of all packets received by this node
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

        # time to broadcast time sync packet
        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 20000

    def setup(self):
        super().setup()

    def update_loop(self):

        super().update_loop()

        if(self.chapter == 0):

            if(self.node.get_transceiver().has_received()):
                # print(self.node.get_transceiver().rec_list)
                rx_packet = self.node.get_transceiver().get_received()
                self.receive(rx_packet)

            # breadcast time sync packet to all nodes every hour
            if(self.last_time_broadcast > 0):
                self.last_time_broadcast -= 1
            else:
                self.last_time_broadcast = self.time_broadcast
                self.node.get_transceiver().send(
                    packet_flooding(
                        self.appID,
                        self.node_id,
                        0,
                        Payload_type.TIME_SYNC,
                        self.node.get_time(),
                        5
                    )
                )
       
        else:
            self.node.wait(10)


