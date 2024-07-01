from logic.handler_flooding_basic import handler_flooding_basic
from logic.logic import logic_node
from hw.packet import packet, Payload_type, Command_type, Packet_type
from typing import List

import os
import datetime
import sqlite3
from sqlite3 import Error

class logic_central(logic_node):

    def __init__(self, appID : int =0, node_id : int = 0) -> None:
        super().__init__(appID, node_id)

        # list of all packets received by this node
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 20000


    def update_loop(self): 
        super().update_loop()

    def receive(self, rx_packet) -> None:
        if(rx_packet.packet_type == Packet_type.LORA):
            # check if its the same network
            if(rx_packet.appID == self.appID):
                if(rx_packet.target == self.node_id or rx_packet.target == 0):
                    if(rx_packet.payload_type is Payload_type.DATA):
                        self.store_packet(rx_packet)
                else:
                    self.packetHandler.handle_packet(rx_packet)


    def store_packet(self, rx_packet):
        self.pack_list.append(rx_packet)

        self.local_db.append(rx_packet)
        self.local_db_rx_time.append(self.node.get_time())

        self.debugger.log("received at central: %s" % str(rx_packet), 2)