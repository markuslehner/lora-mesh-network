from sim.destroyed_packet import destroyed_packet, Destruction_type
from typing import List, Union

class transceiver(object):
    
    def __init__(self, node):
        self.sleep = False
        self.node = node
        self.world = None

        # parameters
        self.frequency : float = 868.0 #Mhz
        self.rec_frequency : List[float]= None
        self.modulation : str = "SF_9"
        self.rec_modulation : List[str] = None
        self.bandwidth : float = 125.0 #kHz
        self.tx_power : float = 20.0 # dBm

        

        # TODO LoRa parameters to subclass
        # self.preamble_length : int = 12  #num symbols
        # self.code_rate = 5 # 4/code_rate * R_b = effective bit rate

        # if true, aborts sending and retries when inc transmission detected
        # This is NOT the case with the used Semtech Transceivers
        self.detect_sending_collisions = False

        # sending logic params
        self.packet_rec = None
        self.send_list = []
        self.rec_list = []
        self.flag_rec = 0
        self.sending = False
        self.receiving = False
        # True when 2 packets received simultaneously
        # OR
        # received packet during sending, does not affect sending
        # used for keeping track of air-time of destroyed receive packet
        # wait for air-time of packet 2
        self.receive_error = False

        # cooldown for sending
        self.cooldown = 0

        # later for sending durations more than one tick
        self.sending_time = 0
        self.receiving_time = 0

        # statistics
        self.cnt_rec = 0                # successful reception
        self.cnt_rec_all = 0            # all packets that reached the receiver
        self.cnt_sen = 0                # successful sending
        self.cnt_destroyed = 0          # nr of packets destroyed
        self.cnt_corrupted = 0          # nr of packets corrupted
        self.list_rec_debug = []        # keep track of all packets that were arriving during a collision
        self.list_rec_time_debug = []   # keep track of time the packets in list_rec_debug arrived
        self.send_error_packet = None   # packet that was sent to write in destroyed packets

    def set_debugger(self, debugger):
        self.debugger = debugger

    def register_in_world(self, world):
        self.world = world

    def set_frequency(self, freq : float):
        self.frequency : float = freq
        if self.rec_frequency is None:
            self.rec_frequency = [freq]

    def get_frequency(self):
        return self.frequency
    
    def set_rec_frequency(self, freq : Union[float, List[float]]):
        self.rec_frequency : List[float] = freq if isinstance(freq, list) else [freq]

    def set_rec_modulation(self, mod : Union[str, List[str]]):
        self.rec_modulation : List[str] = mod if isinstance(mod, list) else [mod]

    def set_modulation(self, mod : str):
        self.modulation : str = mod
        if(self.rec_modulation is None):
            self.rec_modulation = [mod]

    def get_modulation(self):
        return self.modulation

    def set_bandwidth(self, band):
        self.bandwidth = band

    def get_bandwidth(self):
        return self.bandwidth

    def get_tx_power(self):
        return self.tx_power

    """
    set the transmit power of the transceiver
    possible values are 7, 14, 17 and 20 dBm
    """
    def set_tx_power(self, tx_power):
        if(tx_power > 20):
            self.tx_power = 20
        elif(tx_power < 7):
            self.tx_power = 7
        else:
            self.tx_power = tx_power

    def get_power_consumption(self):
        if(self.sleep):
            return 4
        else:
            if(self.sending):
                if(self.tx_power == 20):
                    return 120*1000
                elif(self.tx_power == 17):
                    return 87*1000
                elif(self.tx_power == 14):
                    return 29*1000
                elif(self.tx_power == 7):
                    return 20*1000
                else:
                    return 120*1000
            else:
                return 20*1000

    # incomming transmission
    # does not have to be successfull
    def receive(self, packet, corrupted = False):
        if(not self.sleep):
            # print("received at node %s" % self.node.name)
            if(packet.frequency in self.rec_frequency and packet.modulation in self.rec_modulation and packet.bandwidth == self.bandwidth):
                # print("correct packet received at node %s" % self.node.name)

                self.packet_rec = packet
                self.list_rec_debug.append(self.packet_rec)
                self.list_rec_time_debug.append(self.world.get_time())
                self.flag_rec += 1
                self.cnt_rec_all += 1
                self.receiving = True
                self.receiving_time = self.packet_rec.get_air_time()

                if(corrupted):
                    self.packet_rec.corrupted = True
                    self.handle_error(3)

        else:
            self.debugger.add_destroyed_packet(destroyed_packet(
                    packet,
                    packet.sender,
                    self.node.id,
                    Destruction_type.SLEEP,
                    time=self.world.get_time()
                ))

    # queue the packet
    # send at beginning of next time-slot
    def send(self, packet):
        self.stop_sleep()
        self.send_list.append(packet)

    # update logic
    def update(self):

        if(self.sending):
            # sending error, just for debugging and receiving collision after sending has completed, 
            # but incoming transission (during sending) is still on air
            # --> need to set the receive error flag to keep track of the destroyed packets air-time
            if(self.flag_rec > 0):
                if(self.detect_sending_collisions):
                    self.sending = False
                self.handle_error(0) # 0 = sending collision
            # sent packet
            else:
                if(self.sending_time > 0):
                    self.sending_time -= 1
                else:
                    self.sending_time = 0
                    self.send_list.pop(0)
                    self.sending = False
        else:
            if(self.cooldown > 0):
                self.cooldown -= 1

            # start sending if no cooldown
            if( self.cooldown == 0 and len(self.send_list) > 0):
                self.cnt_sen += 1
                self.send_list[0].send(self.frequency, self.modulation, self.bandwidth, self.tx_power)
                self.debugger.log("%s: sending packet with air-time=%i" % (self.node.name, self.send_list[0].get_air_time()), 4)
                # self.sending_time = world.get_air_time(self.frequency, self.modulation, self.bandwidth, self.send_list[0].get_length())
                self.sending_time = self.send_list[0].get_air_time()
                self.sending = True
                self.world.transmit_packet(self.node, self.send_list[0])
        
        if(self.receiving):
            # error, mulitple transmissions
            if(self.receive_error):

                # check for incomming transmission
                # second receive error  
                if(self.flag_rec > 0):
                    self.handle_error(2)
                
                if(self.receiving_time > 0):
                    self.receiving_time -= 1
                else:
                    self.receive_error = False
                    self.receiving = False
                    # finish receive error
                    self.handle_error(5)

                    # add destroyed packets to debugger
                    for p in range(len(self.list_rec_debug)):
                        self.debugger.add_destroyed_packet(destroyed_packet(
                            self.list_rec_debug[p],
                            self.list_rec_debug[p].sender,
                            self.node.id,
                            Destruction_type.WORLD if self.list_rec_debug[p].corrupted else Destruction_type.COLLISION,
                            collision_packets=self.list_rec_debug + [self.send_error_packet],
                            time=self.list_rec_time_debug[p]
                        ))
                        self.cnt_destroyed += not self.list_rec_debug[p].corrupted

                    self.list_rec_debug = []
                    self.list_rec_time_debug = []
                    self.send_error_packet = None

            else:
                if(self.flag_rec > 1):
                    self.handle_error(1) # 1 = receiving collision
                else:
                    if(self.receiving_time > 0):
                        self.receiving_time -= 1
                    else:
                        self.debugger.log("%s: received packet from node: %i" % (self.node.name, self.packet_rec.sender), 4)
                        self.cnt_rec += 1
                        self.flag_rec = 0
                        # self.rec_list.append(copy.copy( self.packet_rec))
                        self.rec_list.append(self.packet_rec)
                        self.packet_rec.set_receive_time(self.world.get_time())
                        self.packet_rec = None
                        self.receiving = False
                        self.list_rec_debug = []
                        self.list_rec_time_debug = []

    def has_received(self):
        return len(self.rec_list) > 0

    def get_received(self):
        return self.rec_list.pop(0)

    # wrapper to keep update loop neat
    # t - type (0 = sending collision, 1 = receiving collision start, 2 = further receiving collision, 3 = corruption, 5 = finish collision)
    def handle_error(self, t):
        if(t == 0):
            self.debugger.log("%s: sending collision start @ %i  %s" % (self.node.name, self.node.get_time(), self.list_rec_debug[0]), 4)
            self.send_error_packet = self.send_list[0]
            self.receive_error = True
        elif(t == 1):
            self.debugger.log("%s: receiving collision started @ %i  %s" % (self.node.name, self.node.get_time(), self.list_rec_debug[0]), 4)
            self.receive_error = True
        elif(t== 2):
            self.debugger.log("%s: receiving collision @ %i  %s" % (self.node.name, self.node.get_time(), self.list_rec_debug[-1]), 4)
        elif(t== 3):
            self.debugger.log("%s: corruption @ %i  %s" % (self.node.name, self.node.get_time(), self.list_rec_debug[0]), 4)
            self.receive_error = True
            self.cnt_corrupted += 1
            return
        elif(t == 5):
            self.debugger.log("%s: receiving collision ended @ %i, packets destroyed: %i" % (self.node.name, self.node.get_time(), len(self.list_rec_debug)), 4)
            self.debugger.log("  destroyed packets:", 4)
            for i in range(0, len(self.list_rec_debug)):
                self.debugger.log("                     (%s) %s from %i" % ("c" if self.list_rec_debug[i].corrupted else "d" , str(self.list_rec_debug[i]), self.list_rec_time_debug[i]), 4)
 
        self.flag_rec = 0
        self.packet_rec = None

    # ToDo
    # better handling when packets are still being received when going to sleep
    # logic behavior is not compromised, but transceiver still "receives" packet at wake-up
    def start_sleep(self):
        self.sleep = True
    
    def stop_sleep(self):
        self.sleep = False