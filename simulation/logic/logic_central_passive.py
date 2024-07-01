from logic.handler_flooding_basic import handler_flooding_basic
from logic.logic import logic
from logic.logic_central import logic_central
from logic.handler_flooding import handler_flooding
from hw.packet import Payload_type, Command_type, packet_flooding

class logic_central_passive(logic_central):

    def __init__(self, appID=0, node_id : int = 0) -> None:
        super().__init__(appID, node_id)

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


