from datetime import datetime
import signal
import pickle
import os
import sys
import traceback

from rak811.rak811_v3 import Rak811
from rak811.rak811_v3 import Rak811ResponseError, Rak811Error, Rak811TimeoutError

from lib.packet_handler import packet_handler
from lib.logger import logger
import web_server_control

# Magic key to recognize our messages
AppID = b'\xaf\xfe'

# RF configuration
# - Avoid LoRaWan channels (You will get quite a lot of spurious packets!)
# - Respect local regulation (frequency, power, duty cycle)
freq = 865.000
sf = 7
bw = 0  # 125KHz
ci = 1  # 4/5
pre = 12
pwr = 14

# when to reset error_cnt in seconds
error_cooldown = 60*10
# p2p receieve timeout
p2p_timeout = 0.1

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

    if(user):
        # ask user to save state
        print("Save state? (y/n)")
        choice = input()

        if(choice == "y"):
            logger_instance.log("User decided to save state.", 1)
            packet_handler_instance.save_state()
        else:
            logger_instance.log("User decided NOT to save state.", 1)
    else:
        packet_handler_instance.save_state()
        
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
    print("")
    logger_instance.log("PROCESS WAS TERMINATED", 1)
    exit_program()

def check_old_state():
    if(os.path.exists("last_state.pkl")):
        logger_instance.log("Found old state", 1)
        with open("last_state.pkl", "rb") as f:
            config = pickle.load(f)
            # if save time was not more than 30 minutes ago
            if(round(datetime.now().timestamp() * 1000) - config.get("time") < 1000*60*90):
                logger_instance.log("Old state is recent.", 1)
                if(running_as_service):
                    logger_instance.log("Importing old state!", 1)
                    packet_handler_instance.restore_state(config.get("packet_handler"))
                else:
                    print("Found recently saved state, load it? (y/n)")
                    choice = input()

                    if(choice == "y"):
                        logger_instance.log("User decided to import old state!", 1)
                        packet_handler_instance.restore_state(config.get("packet_handler"))
                    else:
                        logger_instance.log("User decided not to import old state!", 1)
            else:
                logger_instance.log("Old state is too old, RESTARTING!", 1)

            if(running_silent): logger_instance.log("DISABLING CONSOLE LOGGING, look at logfile: logs/%s.txt" % logger_instance.file_name , 1)

def run_loop():
    while True:
        global error_cnt, good_cnt, reset_lora
        try:
            # needs to be called to process inc messages
            lora.receive_p2p(p2p_timeout)
            good_cnt += 1

            packet_handler_instance.update_loop()
            logger_instance.update()

            # if message was received
            if lora.nb_downlinks > 0:
                message = lora.get_downlink()
                data = message['data']

                # check if package is from one of our nodes
                # print("  Received packet with length %i" % len(data))
                # print(data)
                if(not data is None and len(data) > 1):
                    if data[:len(AppID)] == AppID:
                        if(len(data) >= 8):
                            packet_handler_instance.receive(data, message['snr'], message['rssi'])
                        else:
                            logger_instance.log('Received message is too short, not handling', 2)
                    else:
                        logger_instance.log('Foreign message received', 2)
                        try:
                            logger_instance.log('  %s' % data.decode(), 2)
                        except:
                            logger_instance.log('Message not decodeable', 2)
                else:
                    logger_instance.log('Message is too short', 2)

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

            # exit triggered by the user with CTRL + C in console
            # this is already handled by signal.SIGINT
            if(not type(ex).__name__ == 'SystemExit'):
                packet_handler_instance.save_state()
                logger_instance.print = True
                logger_instance.log('ENCOUNTERED AN ERROR!!!', 1)
                logger_instance.log(traceback.format_exc(), 1)
                logger_instance.finish()
                print(traceback.format_exc())
                print("EXITING PROGRAM!")
                exit(1) 

        if(error_cnt > 0 and good_cnt > int(error_cooldown / p2p_timeout)):
            error_cnt = 0
        if(reset_lora and good_cnt > int(error_cooldown / p2p_timeout)):
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
                raise Exception("Something is wrong with the LoRa module...")         

if __name__ == "__main__":
    # runtime params
    debug_lvl = 2
    running_as_service = False
    running_silent = False

    # START LOGGING
    logger_instance = logger(debug_lvl, True, "log_start")

    # check for runtime arguments
    if (len(sys.argv) > 1):
        for arg in sys.argv:
            if(arg == "service"):
                running_as_service = True
            elif(arg == "background"):
                running_silent = True
            elif(arg.startswith("debug_lvl")):
                debug_lvl = int(arg.split("=")[1])

    logger_instance.log("STARTED LOGGING:", 1)
    logger_instance.log("  service: %s" % running_as_service, 1)
    logger_instance.log("  silent: %s" % running_silent, 1)
    logger_instance.log("  debug_lvl: %i" % debug_lvl, 1)

    lora = Rak811()

    # Most of the setup should happen only once...
    logger_instance.log('LoRa Setup', 1)
    configure_lora()

    # artificial blocks
    artificial_blocks = [177, 155, 133]

    logger_instance.log("APP-ID: %i" % int.from_bytes(AppID, byteorder="big", signed=False), 1)
    packet_handler_instance = packet_handler("data_db.db", 100, AppID, lora, artificial_blocks, logger_instance)

    check_old_state()

    '''Variables for error handling'''
    # counter of errors close together
    error_cnt = 0
    # counter of good cycles
    good_cnt = 0
    # if lora has been reset resently
    reset_lora = False

    signal.signal(signal.SIGINT, handle_user_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    web_server_control.create_webserver(__name__, packet_handler_instance, False)
    logger_instance.log("SUCCESSFULLY STARTED", 1)
    logger_instance.log("--------------------------------------", 1)
    logger_instance.print = not running_silent
    logger_instance.debug_level = debug_lvl
    run_loop()