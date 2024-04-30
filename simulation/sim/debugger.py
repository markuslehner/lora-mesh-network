import datetime, os
from sim.destroyed_packet import destroyed_packet

class debugger(object):

    def __init__(self, debug : bool, print : bool, world, sim_name : str) -> None:
        super().__init__()
        self.debug : bool = debug
        self.print : bool = print
        self.world = world
        # 0: init   1: running  2: post
        self.state = 0
        # list of destroyed packets
        self.destroyed_packets : dict = {}
        self.log_file = open(os.path.dirname(os.path.dirname(__file__)) + "\\results\\%s_log.txt" % sim_name, "w")
    
    def set_state(self, s):
        self.state = s   

        if(self.state == 0):
            self.log_file.write("====================== SIMULATION PARAMETERS ==========================")
            self.log_file.write("\n")
            if(self.print):
                print("====================== SIMULATION PARAMETERS ==========================")
        elif(self.state == 1):
            self.log_file.write("====================== STARTING SIMULATION ============================")
            self.log_file.write("\n")
            if(self.print):
                print("====================== STARTING SIMULATION ============================")
        elif(self.state == 2): 
            self.log_file.write("====================== SIMULATION RESULTS =============================")
            self.log_file.write("\n")
            if(self.print):
                print("====================== SIMULATION RESULTS =============================")
    
    def log(self, message, level=2, disable_print=False):
        
        if(self.state == 0):
            self.log_file.write(message)
            self.log_file.write("\n")
            if(self.print and not disable_print):
                print(message)

        elif(self.state == 1):
            timestamp = datetime.datetime.fromtimestamp(self.world.get_time()/1000).strftime("%H:%M:%S.%f")[:-3]

            if(self.debug >= level):
                self.log_file.write("(%i)  [%s] %s" % (level, timestamp, message))
                self.log_file.write("\n")
                if(self.print and not disable_print):
                    print("(%i)  [%s] %s" % (level, timestamp, message))
        
        elif(self.state == 2):
            self.log_file.write(message)
            self.log_file.write("\n")
            if(self.print and not disable_print):
                print(message)

    def finish(self):
        self.log_file.close()

    # keep track of packets to check where they were destroyed in a collision or not forwarded
    def add_destroyed_packet(self, rx_packet : destroyed_packet) -> None:

        #set time if it has not been set before
        if(rx_packet.time is None):
            rx_packet.time = self.world.get_time()

        if("%i" % rx_packet.receiver in self.destroyed_packets):
            self.destroyed_packets.get("%i" % rx_packet.receiver).append(rx_packet)
        else:
            self.destroyed_packets.update({"%i" % rx_packet.receiver : [rx_packet]})
        
    # get all packets that were not forwarded, destroyed in the world or had a collision during reception
    def get_destroyed_packets(self, node=0) -> 'list[destroyed_packet]':
        if(node == 0):
            big_list : 'list[destroyed_packet]' = []
            for v in self.destroyed_packets.values():
                big_list += list(v)
            return big_list
        else:
            if("%i" % node in self.destroyed_packets):
                return self.destroyed_packets.get("%i" % node)
            else:
                return []