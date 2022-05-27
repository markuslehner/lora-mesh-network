from sys import exit
import logging
import sqlite3
from sqlite3 import Error
from datetime import datetime
import signal
import struct
import traceback

from rak811.rak811_v3 import Rak811
from rak811.rak811_v3 import Rak811ResponseError, Rak811Error, Rak811TimeoutError

from lib.logger import logger

# Magic key to recognize our messages
AppID = b'\xaf\xfe'#

# RF configuration
# - Avoid LoRaWan channels (You will get quite a lot of spurious packets!)
# - Respect local regulation (frequency, power, duty cycle)
freq = 868.000
sf = 7
bw = 0  # 125KHz
ci = 1  # 4/5
pre = 12
pwr = 14

def configure_lora():
    # Set module in LoRa P2P mode
    response = lora.set_config('lora:work_mode:1')
    for r in response:
        logger_instance.log(r, 1)

    lora.set_config(f'lorap2p:{int(freq*1000*1000)}:{sf}:{bw}:{ci}:{pre}:{pwr}')
    lora.set_config('lorap2p:transfer_mode:1')

    logger_instance.log("  Successfully configured LoRa:", 1)
    logger_instance.log("    %s: %s" % (str("freq").rjust(10), str(freq).ljust(10)), 1)
    logger_instance.log("    %s: %s" % (str("SF").rjust(10), str(sf).ljust(10)), 1)
    logger_instance.log("    %s: %s" % (str("BW").rjust(10), str(bw).ljust(10)), 1)
    logger_instance.log("    %s: %s" % (str("CR").rjust(10), str(ci).ljust(10)), 1)
    logger_instance.log("    %s: %s" % (str("pre").rjust(10), str(pre).ljust(10)), 1)
    logger_instance.log("    %s: %s" % (str("pwr").rjust(10), str(pwr).ljust(10)), 1)

def exit_program(user : bool =False):
    logger_instance.log("CLEAN UP...", 1)
        
    lora.close()

    logger_instance.log("EXITING PROGRAM!", 1)
    logger_instance.finish()
    exit(1)

def handle_user_interrupt(signum, frame):
    logger_instance.print = True
    print("")
    logger_instance.log("PROCESS WAS INTERRUPTED BY USER", 1)
    exit_program(user=True)

def handle_interrupt(signum, frame):
    logger_instance.print = True
    logger_instance.log("PROCESS WAS TERMINATED", 1)
    exit_program()

def run_loop():
    logger_instance.log('Entering send/receive loop')

    while True:
        global error_cnt, good_cnt, reset_lora
        try:
            # needs to be called to process inc messages
            lora.receive_p2p(5)
            good_cnt += 1

            logger_instance.update()

            # if message was received
            if lora.nb_downlinks > 0:
                message = lora.get_downlink()
                data = message['data']

                if data[:len(AppID)] == AppID:
                    node_id = data[3]

                    type = "DATA" if data[8] == 0 else "OTHER"

                    logger_instance.log("%s from node %i  @ %s" % (type, node_id, datetime.now().strftime("%H:%M:%S")) )
                    
                    logger_instance.log("  Sender: %i" % data[2])
                    logger_instance.log("  Origin: %i" % data[3])
                    logger_instance.log("  Target: %i" % data[4])
                    logger_instance.log("  Hops: %i / %i" % (data[5]&15, data[5]>>4))
                    logger_instance.log("  Packet-ID: %i" % data[6])
                    logger_instance.log("  Dir: %i, last_dist: %i" % ( data[7]>>7, data[7]&127 ))
                    logger_instance.log("  PL-Type: %i" % data[8])

                    if(data[8] == 0):
                        lat = struct.unpack('d', data[9:17])[0]
                        long = struct.unpack('d', data[17:25])[0]
                        bat = data[25]
                        logger_instance.log("  CONTENTS:")
                        logger_instance.log("    latitude: %.4f" % lat)
                        logger_instance.log("    longitude: %.4f" % long)
                        logger_instance.log("    battery: %i" % (bat))

                    logger_instance.log('RSSI: {}, SNR: {}'.format(message['rssi'], message['snr']))

                    # save message to database
                    p_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    db_packet = ('Sensor_%s' % str(data[len(AppID)+1:len(AppID)+2][0]).zfill(2), "DATA", lat, long, bat, message['rssi'], message['snr'], p_time)
                    cur = conn.cursor()
                    cur.execute(sql, db_packet)
                    conn.commit()
                    logger_instance.log("Saved packet to db at index: %i" % cur.lastrowid, 2)

                    # # answer
                    # # Set module in send mode
                    # lora.set_config('lorap2p:transfer_mode:2')

                    # p = packet(AppID, 0, node_id, 10, counter, 0, 0, Payload_type.ACK, None)
                    # data = p.to_bytes()

                    # lora.send_p2p(data)
                    # # back to receive
                    # lora.set_config('lorap2p:transfer_mode:1')

                    # logger_instance.log('Sent response message %i with lenght %i' % (counter, len(data)))
                    # counter += 1
                else:
                    logger_instance.log('Foreign message received')
        except Rak811ResponseError:
            logger_instance.log("Encountered Error: Rak811ResponseError", 1)
            good_cnt = 0
            error_cnt += 1
        except Rak811TimeoutError:
            logger_instance.log("Encountered Error: Rak811TimeoutError", 1)
            good_cnt = 0
            error_cnt += 1
        except Rak811Error:
            logger_instance.log("Encountered Error: Rak811Error", 1)
            good_cnt = 0
            error_cnt += 1
        except Exception as ex:
            logger_instance.log('ENCOUNTERED AN ERROR!!!', 1)
            logger_instance.finish()
            print(traceback.format_exc())
            print("EXITING PROGRAM!")
            exit(1)  

        if(error_cnt > 0 and good_cnt > int(60 * 10 / 5)):
            error_cnt = 0
        if(reset_lora and good_cnt > int(60 * 10 / 5)):
            reset_lora = False

        if(error_cnt > 3):
            if(not reset_lora):
                logger_instance.log("Too many errors in a row occurred, resetting LoRa", 1)
                logger_instance.log("  good_cnt: %i" % good_cnt, 2)
                error_cnt = 0
                reset_lora = True
                lora.hard_reset()
                configure_lora()
            else:
                logger_instance.log("Not fixable, aborting")
                logger_instance.log("  good_cnt: %i" % good_cnt, 2)
                exit_program()

if __name__ == "__main__":
    # START LOGGING
    logger_instance = logger(2, True, "log_gps")

    lora = Rak811()

    debug = False
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    
    # Most of the setup should happen only once...
    logger_instance.log('Setup')
    configure_lora()

    # connect to database
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        logger_instance.log("opening db: gps_db_%i.db" % int(sf))
        conn = sqlite3.connect("gps_db_%i.db" % int(sf))
    except Error as e:
        logger_instance.log(e)

    # store command
    sql = ''' INSERT INTO packets(sender,type,latitude,longitude,battery,rssi,snr,time_received)
            VALUES(?,?,?,?,?,?,?,?) '''

    logger_instance.log("APP-ID: %i" % int.from_bytes(AppID, byteorder="big", signed=False))

    '''Variables for error handling'''
    # counter of errors close together
    error_cnt = 0
    # counter of good cycles
    good_cnt = 0
    # if lora has been reset resently
    reset_lora = False

    signal.signal(signal.SIGINT, handle_user_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    logger_instance.log("SUCCESSFULLY STARTED")
    logger_instance.log("--------------------------------------")
    run_loop()