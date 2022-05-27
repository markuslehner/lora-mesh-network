from datetime import datetime
import signal
import time

from lib.packet_handler import packet_handler
from lib.logger import logger

import web_server_control

debug_lvl = 2

logger_instance = logger(debug_lvl, True, None)
packet_handler_instance = packet_handler("data_db.db", 100, None, None, None, logger_instance)

# create dummy values
packet_handler_instance.num_connected_nodes = 4
packet_handler_instance.node_ids = [3, 5, 11, 27]
packet_handler_instance.node_distances = [1, 2, 3, 3]
packet_handler_instance.node_of_first_contact = [packet_handler_instance.id, 3, 5, 5]
packet_handler_instance.node_battery_level = [89, 23, 15, 23]

packet_handler_instance.routes.append([5, 100])
packet_handler_instance.routes.append([27, 3, 100])
packet_handler_instance.routes.append([27, 3, 5])

packet_handler_instance.num_tx_after_start=24
packet_handler_instance.num_rx_after_start=22
packet_handler_instance.time_started = 214318513
packet_handler_instance.time_restarted = 214518513

def handle_interrupt(signum, frame):
    print("")
    logger_instance.log("RECEIVED INTERRUPT, SHUTTING DOWN!", 1)
    logger_instance.log("CLEAN UP...",1)
    logger_instance.finish()
    print("EXITING PROGRAM!")
    exit(1)

def run_loop():
    while True:
        time.sleep(0.1)
       
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_interrupt)
    web_server_control.create_webserver(__name__, packet_handler_instance, False)
    run_loop()