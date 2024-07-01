from logic.handler_flooding_basic import handler_flooding_basic
from logic.logic import logic, logic_node
from hw.packet import packet, Payload_type, Command_type, Packet_type
from typing import List

import os
import datetime
import sqlite3
from sqlite3 import Error

class logic_central(logic_node):

    def __init__(self, appID : int =0, node_id : int = 0, db :bool=False, handler=handler_flooding_basic()) -> None:
        super().__init__(appID, node_id, handler)

        # list of all packets received by this node
        self.pack_list : List[packet] = []
        # list of all packets stored to db for easier access
        self.local_db : List[packet] = []
        self.local_db_rx_time : List[float]= []

        self.time_broadcast = 1000*60*60
        self.last_time_broadcast = 20000
        self.write_db = db

    def setup(self):
        self.node.get_transceiver().set_frequency(868)
        self.node.get_transceiver().set_modulation("SF_10")
        self.node.get_transceiver().set_tx_power(14)

        self.packetHandler.register(self.node)

        if(self.write_db):
        # database
            database = r"Simulation\db\testdb.db"
            if os.path.exists(database):
                os.remove(database)

            print(os.getcwd())
            sql_create_packets_table = """ CREATE TABLE IF NOT EXISTS packets (
                                            id integer PRIMARY KEY,
                                            sender text,
                                            type text NOT NULL,
                                            data text,
                                            time_received text
                                        ); """
            self.conn = None
            try:
                self.conn = sqlite3.connect(database)
            except Error as e:
                print(e)

            try:
                c = self.conn.cursor()
                c.execute(sql_create_packets_table)
            except Error as e:
                print(e)

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

        if(self.write_db):
            """
            Create a new packet into the packets table
            :param conn:
            :param packet:
            :return: project id
            """
            sql = ''' INSERT INTO packets(sender,type,data,time_received)
                    VALUES(?,?,?,?) '''
            cur = self.conn.cursor()
            cur.execute(sql, (
                rx_packet.origin,
                str(rx_packet.payload_type)[13:],
                rx_packet.payload,
                datetime.datetime.fromtimestamp(int(self.node.get_time()/1000)).strftime("%H:%M:%S")
            ))
            self.conn.commit()

