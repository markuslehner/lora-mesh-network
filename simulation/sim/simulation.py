from sim.world import world
from hw.node import node
from hw.node_sensor import node_sensor
from logic.logic import logic, logic_node
from logic.logic_central import logic_central
from sim.debugger import debugger
from sim.destroyed_packet import destroyed_packet, Destruction_type
from datetime import datetime

import pickle, os, time
import numpy as np
from pathlib import Path

class simulation(object):

    def __init__(self, configuration, name, debug=None, runtime=None, visualize=None, print_debug=True, real_time=False, log_bat = False, bat_log_id = []) -> None:
        super().__init__()
        self.name = name
        self.real_time = real_time

        with open(str(Path(__file__).parent.parent) + "/config/%s.pkl" % configuration, "rb") as f:
            config = pickle.load(f)

        """
        SETUP PARAMETERS
        """
        # simulation time in ms
        if(runtime is None):
            self.runtime = config.get("config").get("runtime")
        else:
            self.runtime = runtime

        # time for world in ms
        self.world_time = config.get("config").get("world_time")
        # run in new thread in background
        # only output to txt file
        self.background = config.get("config").get("background")

        self.additionalInfo = config.get("config").get("runtime")

        # 0 - Off
        # 1 - light
        # 2 - mid
        # 3 - heavy
        # 4 - all
        if(debug is None):
            self.debug = config.get("config").get("debug")   
        else:
            self.debug = debug

        # log battery
        self.log_battery = log_bat
        # node ids to log
        self.log_battery_ids = bat_log_id
        # battery log interval
        self.battery_log_interval = 1000*60

        # create log arrays
        self.battery_logs = np.zeros((len(self.log_battery_ids), 1 + int(self.runtime/self.battery_log_interval )))
            
        # plot visualization of map
        if(visualize is None):
            self.visualize = config.get("config").get("visualize")
        else:
            self.visualize = visualize

        self.use_same_offset = config.get("config").get("use_same_offset")

        self.num_nodes = config.get("config").get("num_nodes")
        self.num_blocks = config.get("config").get("num_blocks")

        """
        load world params
        create world
        """

        self.my_world = world(
            config.get("world").get("tx_min"), 
            config.get("world").get("tx_max"), 
            config.get("world").get("tx_error_rate"), 
            config.get("world").get("tx_decay")
            )

        self.debugger = debugger(self.debug, print_debug, self.my_world, self.name)
        self.debugger.set_state(0)
        self.my_world.set_debugger(self.debugger)
        self.my_world.set_time(self.world_time)

        """
        load and create nodes
        """

        self.nodes = []
        self.central_nodes = []

        for i in range(0, self.num_nodes):
            self.nodes.append( config.get("nodes").get(str(i)).get("type").from_dict(config.get("nodes").get(str(i))) )
            if(isinstance(self.nodes[i].logic, logic_central) ):
                self.nodes[i].set_time(self.world_time)
                self.central_nodes.append(self.nodes[i])
            self.nodes[i].set_debugger(self.debugger)

        self.blocks = config.get("blocks")

        for n in self.nodes:
            self.my_world.add(n, n.x, n.y)
        
        for b in self.blocks:
            self.my_world.block_path(b[0], b[1])

        '''
        EVENTS
        '''
        self.event_list = config.get("events")

        if(self.visualize):
            self.my_world.visualize()

        '''
        STATISTICS
        '''
        self.statistics : dict = {}

    def prepare(self):
        self.debugger.log("WORLD:")
        self.my_world.print_state()

        self.debugger.log("NODES:")
        for n in self.my_world.get_nodes():
            self.debugger.log("    %s" % str(n))

        self.debugger.set_state(1)

    def run(self) -> float:

        self.start_time = time.time() * 1000

        # get battery indices
        bat_log_idxs = []
        for n_id in self.log_battery_ids:
            for i in range(len(self.my_world.nodes)):
                if(self.my_world.nodes[i].id == n_id):
                    bat_log_idxs.append(i)
                    break

        bat_log_idx = 0
        for i in range(self.runtime):
            
            start_of_cycle = time.time()
            # print("Time in ms: %f" %  ( start_of_cycle*1000) )
            # check for trigger of event
            # support for more central nodes not implemented
            for e in self.event_list:
                if(e.execution_time == self.world_time + i):
                    e.execute(self.my_world, self.central_nodes[0].logic)

            # log battery
            if(self.log_battery):
                if(i % self.battery_log_interval == 0):
                    for k in range(len(bat_log_idxs)):
                        self.battery_logs[k, bat_log_idx] = self.my_world.nodes[bat_log_idxs[k]].battery.get_level()
                    bat_log_idx+=1
            
            self.my_world.update()

            if(self.real_time):
                end_of_cyle = time.time()
                # print("updating took %f us" %  ( end_of_cyle - start_of_cycle) )
                if( end_of_cyle - start_of_cycle < 0.001): 
                    # print("sleep")
                    # print("sleep for %f" % (0.0005 - (end_of_cyle - start_of_cycle) )) 
                    time.sleep(0.001 - (end_of_cyle - start_of_cycle) )

        if(self.log_battery):
            np.save(str(Path(__file__).parent.parent) + "/results/battery_logs.npy", self.battery_logs)

        self.end_time = time.time() * 1000

    def analyze(self, dont_print_additional=True):
        """
        post simulation analysis
        """
        self.debugger.set_state(2)
        sensor_nodes = []
        node_ids = []
        tx_cnt = []
        total_tx_cnt = 0
        total_rx_cnt = 0

        world_nodes : 'list[node]'=  self.my_world.get_nodes()

        missing_packets, multiple_packets = self.check_received_packets()

        for i in range(len(world_nodes)):
            if(type(world_nodes[i]) is node_sensor):
                sensor_nodes.append(world_nodes[i])
                node_ids.append(world_nodes[i].id)
                tx_cnt.append(world_nodes[i].logic.send_cnt)
                total_tx_cnt += world_nodes[i].logic.send_cnt
            else:
                tx_cnt.append(0)

        rx_cnt = np.zeros((len(world_nodes)))

        for i in range(len(missing_packets)):
            rx_cnt[i] = tx_cnt[i] - len(missing_packets[i])
            total_rx_cnt +=  rx_cnt[i]
            
        self.statistics.update({"total_rx_cnt" : total_rx_cnt})
        self.statistics.update({"total_tx_cnt" : total_tx_cnt})

        seconds=(self.runtime/1000)%60
        seconds = int(seconds)
        minutes=(self.runtime/(1000*60))%60
        minutes = int(minutes)
        hours= int(self.runtime/(1000*60*60))

        elapsed_time = self.end_time - self.start_time
        milis_sim = int( (elapsed_time)%1000 )
        seconds_sim=  int( (elapsed_time/1000)%60 )
        minutes_sim=  int( (elapsed_time/(1000*60))%60 )

        self.debugger.log("Simulation took: %i min %i.%i s" % (minutes_sim, seconds_sim, milis_sim))
        self.debugger.log("Simulated time: %s:%s:%s" % (str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2) ))

        self.debugger.log("nodes sent in total: %i" % total_tx_cnt)
        # this is only the packets the nodes actually sent, so when a nodes loses power
        # it doesn't send, but central thinks it should be sending
        # Because of this the number here may differ from "received after start"
        # This is more indicative of packet loss characteristic when transmitting
        # the other more indicative of overall network performance
        self.debugger.log("received in total: %i / %i = %.2f %s" % ( total_rx_cnt, total_tx_cnt, 100*total_rx_cnt / float(total_tx_cnt), '%' ) )
        self.statistics.update({"received_total" : total_rx_cnt / float(total_tx_cnt)})

        if(hasattr(self.central_nodes[0].logic, 'num_not_received_on_first_try')):
            if(self.central_nodes[0].logic.num_tx_after_start > 0):
                after_start_frac = self.central_nodes[0].logic.num_rx_after_start / float(self.central_nodes[0].logic.num_tx_after_start)
            else:
                after_start_frac = 0

            self.debugger.log("received after start in total: %i / %i = %.2f %s" % ( self.central_nodes[0].logic.num_rx_after_start, self.central_nodes[0].logic.num_tx_after_start, 100*after_start_frac, '%' ) )
            self.statistics.update({"received_after_start" : after_start_frac})

            if(self.central_nodes[0].logic.successfully_started):
                self.debugger.log("received after start in total (without requested packets): %i / %i = %.2f %s" % ( self.central_nodes[0].logic.num_rx_after_start - self.central_nodes[0].logic.num_not_received_on_first_try, self.central_nodes[0].logic.num_tx_after_start, 100*(self.central_nodes[0].logic.num_rx_after_start - self.central_nodes[0].logic.num_not_received_on_first_try) / float(self.central_nodes[0].logic.num_tx_after_start), '%' ) )
                self.statistics.update({"received_after_start_no_request" : (self.central_nodes[0].logic.num_rx_after_start - self.central_nodes[0].logic.num_not_received_on_first_try) / float(self.central_nodes[0].logic.num_tx_after_start)})
        
        self.debugger.log("NODES:")
        if(self.additionalInfo):
            for n in world_nodes:
                # if(not isinstance(n.logic, logic_central)):
                #     if(hasattr(n.logic, 'distance')):
                #         self.debugger.log("sensor-node %s [distance: %s] started with an interval delay of: %i" % (str(n.name).rjust(10), str(int(n.logic.distance)).rjust(2), n.logic.start_time_offset) )
                #     else:
                #         self.debugger.log("sensor-node %s  started with an interval delay of: %i" % (str(n.name).rjust(10), n.logic.start_time_offset) )

                if(hasattr(n.logic, 'distance')):
                    if(n.battery is None):
                        self.debugger.log("  node: %s distance: %s" % (str(n.name).rjust(10), str(int(n.logic.distance)).rjust(3)))
                    else:
                        self.debugger.log("  node: %s distance: %s battery: %s %%" % (str(n.name).rjust(10), str(int(n.logic.distance)).rjust(3), ("%.2f" % (100*n.battery.get_level())).rjust(5) ))

            for i in range(0, len(world_nodes)):
                if(not isinstance(world_nodes[i].logic, logic_central)):
                # if(type(world_nodes[i].logic) is logic_flooding_join or type(world_nodes[i].logic) is logic_flooding or type(world_nodes[i].logic) is logic_node_dist):
                    self.debugger.log("received from %s: %i from %i" % (world_nodes[i].name, rx_cnt[i], world_nodes[i].logic.send_cnt))
                else:
                    self.debugger.log("received from %s: %i" % (world_nodes[i].name, rx_cnt[i]))

            self.debugger.log("DESTROYED", disable_print=dont_print_additional)
            for n in world_nodes:
                self.debugger.log("    %s destroyed packets %i" % (n.name, n.get_transceiver().cnt_destroyed), disable_print=dont_print_additional )
            
            self.debugger.log("CORRUPTED", disable_print=dont_print_additional)
            for n in world_nodes:
                self.debugger.log("    %s corrupted packets %i" % (n.name, n.get_transceiver().cnt_corrupted), disable_print=dont_print_additional )

            self.debugger.log("SENT", disable_print=dont_print_additional)
            for n in world_nodes:
                self.debugger.log("    %s sent in total: %i" % (n.name, n.get_transceiver().cnt_sen), disable_print=dont_print_additional )

            self.debugger.log("RECEIVED", disable_print=dont_print_additional)
            for n in world_nodes:
                self.debugger.log("    %s successfully received: %i from %i (%i)" % (n.name, n.get_transceiver().cnt_rec, n.get_transceiver().cnt_rec_all, n.get_transceiver().cnt_rec + n.get_transceiver().cnt_corrupted + n.get_transceiver().cnt_destroyed), disable_print=dont_print_additional )

        # write CSV results file
        res_file = open(os.path.dirname(os.path.dirname(__file__)) + "\\results\\%s_res.csv" % self.name, "w")

        res_file.write("nodes")
        for n in world_nodes:
            res_file.write(";%s" % n.name)
        res_file.write("\n")

        res_file.write("node ids")
        for n in world_nodes:
            res_file.write(";%s" % n.id)
        res_file.write("\n")

        res_file.write("received DATA packets")
        for rx in rx_cnt:
            res_file.write(";%i" % rx)
        res_file.write("\n")

        res_file.write("from sent DATA packets")
        for i in range(0, len(world_nodes)):
            if( isinstance(world_nodes[i].logic, logic_node) ):
                res_file.write(";%i" % world_nodes[i].logic.send_cnt)
            else:
                res_file.write(";%i" % 0)
        res_file.write("\n")

        res_file.write("received DATA packets before start")
        for n in range(len(world_nodes)):
            if(isinstance(world_nodes[n].logic, logic_central)):
                res_file.write(";%i" % 0)
            else:
                if(hasattr(self.central_nodes[0].logic, "successfully_started") and self.central_nodes[0].logic.successfully_started):
                    res_file.write(";%i" % self.central_nodes[0].logic.statistics.get("num_rx_before_start").get(str(int(world_nodes[n].id))))
                else:
                    res_file.write(";%i" % rx_cnt[n])
        res_file.write("\n")

        res_file.write("received DATA packets after start")
        for n in world_nodes:
            if(isinstance(n.logic, logic_central)):
                res_file.write(";%i" % 0)
            else:
                if(hasattr(self.central_nodes[0].logic, "successfully_started") and self.central_nodes[0].logic.successfully_started):
                    res_file.write(";%i" % self.central_nodes[0].logic.statistics.get("num_rx_after_start").get(str(int(n.id))))
                else:
                    res_file.write(";%i" % 0)
        res_file.write("\n")

        res_file.write("received requested DATA packets after join")
        for n in world_nodes:
            if(isinstance(n.logic, logic_central)):
                res_file.write(";%i" % 0)
            else:
                if(hasattr(self.central_nodes[0].logic, "successfully_started") and self.central_nodes[0].logic.successfully_started):
                    res_file.write(";%i" % self.central_nodes[0].logic.statistics.get("num_rx_requested").get(str(int(n.id))))
                else:
                    res_file.write(";%i" % 0)
        
        res_file.write("\n")

        res_file.write("from sent DATA packets after join")
        for n in world_nodes:
            if(isinstance(n.logic, logic_central)):
                res_file.write(";%i" % 0)
            else:
                if(hasattr(self.central_nodes[0].logic, "successfully_started") and self.central_nodes[0].logic.successfully_started):
                    res_file.write(";%i" % ( self.central_nodes[0].logic.interval_count - self.central_nodes[0].logic.statistics.get("start_interval") ) )
                else:
                    res_file.write(";%i" % 0)
        res_file.write("\n")

        res_file.write("destroyed packets")
        for n in world_nodes:
            res_file.write(";%s" % n.get_transceiver().cnt_destroyed)
        res_file.write("\n")

        res_file.write("sent packets")
        for n in world_nodes:
            res_file.write(";%s" % n.get_transceiver().cnt_sen)
        res_file.write("\n")

        res_file.write("successfully received packets")
        for n in world_nodes:
            res_file.write(";%s" % n.get_transceiver().cnt_rec)
        res_file.write("\n")

        res_file.write("total received packets")
        for n in world_nodes:
            res_file.write(";%s" % n.get_transceiver().cnt_rec_all)
        res_file.write("\n")

        res_file.close()

    def further_analysis(self, print_packets=True, more_info=False, fwd_reasons_to_print=None):
        
        self.debugger.log(" --> FURTHER ANALYSIS")

        node_ids = []
        world_nodes = self.my_world.get_nodes()
        destroyed_packets : 'list[destroyed_packet]' = self.debugger.get_destroyed_packets()

        """
        Evaluate cause of destruction
        """
        self.debugger.log("PACKETS RECEIVED IN DETAIL:")

        for i in range(len(world_nodes)):
            self.debugger.log("  %s" % world_nodes[i].name )
            destroyed_packets_node : 'list[destroyed_packet]' = self.debugger.get_destroyed_packets(world_nodes[i].id)

            # world, forward, collision, sleep
            num_per_class = np.zeros((4))
            
            for pkg in destroyed_packets_node:
                num_per_class[pkg.reason.value-1] += 1
                # if(pkg.reason == Destruction_type.COLLISION):
                #     self.debugger.log("      %s" % str(pkg))

            self.debugger.log("    world: %i, forward: %i, collision: %i, sleep: %i" % (num_per_class[0], num_per_class[1], num_per_class[2], num_per_class[3]) )


        missing_packets, multiple_packets = self.check_received_packets()

        for i in range(len(world_nodes)):
            # if(type(world_nodes[i]) is node_sensor):
            node_ids.append(world_nodes[i].id)

        # only possible for children of logic_central
        if(isinstance(self.central_nodes[0].logic, logic_central) ):

            rx_central = self.central_nodes[0].logic.local_db
            rx_central_times = self.central_nodes[0].logic.local_db_rx_time

            """
            check where packet was destroyed
            also check tx error --> more tricky needs to be done in world
            possible wrapper for packets --> destroyed packet + reason + location
            """
            
            cnt_destroyed_in_world = 0
            cnt_destroyed_total = 0

            cnt_only_destroyed_in_world = 0
            cnt_missing_total = 0


            """
            Print all copies of the missing DATA packe to allow tracing the cause of transmission error
            """
            for n in range(len(node_ids)):
                if len(missing_packets[n]) > 0:
                    self.debugger.log("missing packets from node %i: %i" % (node_ids[n], len(missing_packets[n])) )
                    cnt_missing_total += len(missing_packets[n])
                    for p in missing_packets[n]:
                        if(print_packets): self.debugger.log(p)

                        # counter for other reasons than world, if > 0 then packet does not count as destructed by world
                        cnt_other = 0
                        # loop over all destroyed packets
                        # check if name is same as missing packet
                        # if yes, print reason why this copy of the packet was destroyed (if more_info = True)
                        for l in destroyed_packets:
                            if(l.packet.debug_name == p):
                                cnt_destroyed_total += 1
                                if(more_info and print_packets): 
                                    # only for forward reasons
                                    if(l.reason is Destruction_type.FORWARD):
                                        # if no reasons provided, print all
                                        if(fwd_reasons_to_print is None):
                                            self.debugger.log("    %s" % str(l))
                                        else:
                                            if(l.fwd_reason in fwd_reasons_to_print):
                                                self.debugger.log("    %s" % str(l))
                                    else:
                                        self.debugger.log("    %s" % str(l))

                                if(l.reason == Destruction_type.WORLD):
                                    cnt_destroyed_in_world += 1
                                else:
                                    cnt_other += 1

                        if(cnt_other == 0):
                            cnt_only_destroyed_in_world += 1

            sum_multiple = 0
            for n in range(len(node_ids)):
                if len(multiple_packets[n]) > 0:
                    self.debugger.log("multiple packets from node %i: %i" % (node_ids[n], len(multiple_packets[n])) )
                    sum_multiple += len(multiple_packets[n])
                    for p in multiple_packets[n]:
                        if(print_packets): self.debugger.log(p)
                        for i in range(len(rx_central)):
                            if(rx_central[i].debug_name == p):
                                if(more_info and print_packets): self.debugger.log("Through hops: %s received at %s" % (str(rx_central[i].hops), datetime.fromtimestamp(rx_central_times[i]/1000).strftime("%H:%M:%S.%f")[:-3]))

            self.debugger.log("EVALUATION")

            self.debugger.log("Analysis where the missing packets were destroyed:")   

            destroyed_total_percentage = 0 if(cnt_destroyed_total == 0) else 100.0*cnt_destroyed_in_world/cnt_destroyed_total
            destroyed_world_only_percentage = 0 if(cnt_missing_total == 0) else 100.0*cnt_only_destroyed_in_world/cnt_missing_total

            self.debugger.log("%.2f %s of missing packets were destroyed in the world (%i of %i destroyed)" % (destroyed_total_percentage, "%", cnt_destroyed_in_world, cnt_destroyed_total))
            self.debugger.log("%.2f %s of missing packets were only destroyed in the world (%i of %i missing)" % (destroyed_world_only_percentage, "%", cnt_only_destroyed_in_world, cnt_missing_total))
            self.debugger.log("%i multiple packets were received in total" % (sum_multiple))


            # # print all packets 
            # for n in node_ids:
            #     for i in range(len(rx_central)):
            #         if(rx_central[i].origin == n):
            #             print("%s received at %i" % (str(rx_central[i]), rx_central_times[i]) )

            # # print all packets at central
            # for p in self.central_nodes[0].logic.pack_list:
            #     self.debugger.log("%s received at %s" % (p, datetime.fromtimestamp(p.time_received/1000).strftime("%H:%M:%S.%f") ) )

    def check_received_packets(self):

        node_ids = []
        node_tx_cnt = []
        world_nodes = self.my_world.get_nodes()
        sensor_nodes = []

        for i in range(len(world_nodes)):
            sensor_nodes.append(world_nodes[i])
            node_ids.append(world_nodes[i].id)
            if(type(world_nodes[i]) is node_sensor):
                node_tx_cnt.append(world_nodes[i].logic.send_cnt)
            else:
                node_tx_cnt.append(0)

        missing_packets = []
        multiple_packets = []

        # only possible for subclasses of logic_central
        if(isinstance(self.central_nodes[0].logic, logic_central) ):

            rx_central = self.central_nodes[0].logic.local_db
            rx_central_times = self.central_nodes[0].logic.local_db_rx_time

            """
            check which packets are missing
            """
            # all packets that were received from node with index from node_ids
            rx_from_node = []

            for n in range(len(node_ids)):
                rx_from_node.append([])
                for i in range(len(rx_central)):
                    if(rx_central[i].origin == node_ids[n]):
                        rx_from_node[n].append(rx_central[i])

            # check which packets were received
            # debug_name = node.name + "_" + send_cnt
            for n in range(len(node_ids)):
                missing_packets.append([])
                multiple_packets.append([])
                rx_cnt = np.zeros((node_tx_cnt[n]))

                for rx_packet in rx_from_node[n]:
                    if(not rx_packet.debug_name is None and str(rx_packet.debug_name).startswith(sensor_nodes[n].name)):
                        packet_nr = int(rx_packet.debug_name.replace("%s_" % sensor_nodes[n].name, ""))
                        rx_cnt[packet_nr-1] += 1

                for k in range(node_tx_cnt[n]):
                    if(rx_cnt[k] == 0):
                        missing_packets[n].append("%s_%i" % (sensor_nodes[n].name, k+1))
                    elif(rx_cnt[k] > 1):
                        multiple_packets[n].append("%s_%i" % (sensor_nodes[n].name, k+1))


        return missing_packets, multiple_packets

    # check if keyword is valid statistic
    # yes --> return it
    # no  --> return 0 
    def get_stat(self, keyword : str):
        if(keyword in self.statistics):
            return self.statistics.get(keyword)
        else:
            print("Not a valid statistic, or it has not been calculated yet.")
            return 0

    def stop(self):
        print("SIMULATION: ToDo: clean up!")
        self.debugger.finish()




        





    