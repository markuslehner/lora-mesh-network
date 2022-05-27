import sqlite3
from sqlite3 import Error
import datetime
import struct

from lib.logger import logger

# store commands
sql_gps = ''' INSERT INTO packets(sender,type,latitude,longitude,battery,rssi,snr,time_received)
    VALUES(?,?,?,?,?,?,?,?) '''

sql_data = ''' INSERT INTO packets(sender,type,temp,acc_x,acc_y,acc_z,battery,rssi,snr,time_received)
    VALUES(?,?,?,?,?,?,?,?,?,?) '''

class packet_db(object):

    def __init__(self, db_name, logger : logger) -> None:
        super().__init__()

        self.logger = logger

        try:
            self.conn = sqlite3.connect(db_name)
        except Error as e:
            print(e)

    def store_gps(self, rx_packet):
        # save message to database
        p_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        p_data = rx_packet.payload

        lat = struct.unpack('d', p_data[0:8])[0]
        long = struct.unpack('d', p_data[8:16])[0]
        bat = p_data[16]

        db_packet = ('Sensor_%s' % str(rx_packet.origin).zfill(2), str(rx_packet.payload_type), lat, long, bat, rx_packet.rssi, rx_packet.snr, p_time)
        cur = self.conn.cursor()
        cur.execute(sql_gps, db_packet)
        self.conn.commit()
        self.logger.log("  stored in db @%i" % cur.lastrowid, 3)

    def store_data(self, rx_packet):
        # save message to database
        p_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        p_data = rx_packet.payload

        temp = struct.unpack('f', p_data[0:4])[0]
        self.logger.log("  temp: %.2f" % temp, 4)
        acc_x = struct.unpack('f', p_data[4:8])[0]
        acc_y = struct.unpack('f', p_data[8:12])[0]
        acc_z = struct.unpack('f', p_data[12:16])[0]
        bat = p_data[16]

        db_packet = ('Sensor_%s' % str(rx_packet.origin).zfill(2), str(rx_packet.payload_type), temp, acc_x, acc_y, acc_z, bat, rx_packet.rssi, rx_packet.snr, p_time)
        cur = self.conn.cursor()
        cur.execute(sql_data, db_packet)
        self.conn.commit()
        self.logger.log("  stored in db @%i" % cur.lastrowid, 3)