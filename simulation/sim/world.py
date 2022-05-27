import numpy as np
import random

from hw.node_sensor import node_sensor
from hw.node import node
from sim.debugger import debugger
from sim.destroyed_packet import destroyed_packet, Destruction_type

import matplotlib.pylab as plt
import matplotlib.patches as patches
import tikzplotlib

import math
import copy
import re
from pathlib import Path

"""
MIN_DISTANCE
below this distance the signal is only affected by the static error_rate

MAX_DISTANCE
max distance a signal can be received
if distance is higher, then no transmission is possible

ERROR_RATE
probability of an error occurring during transmission, not affected by range

DECAY
decay of an exp function
    fact = (dist - min_dist) / (max_dist - min_dist)
    np.exp(decay * fact * (-1) )
this is used to calculate the drop-off in link quality between
min_distance and max_distance
"""
transmission_ranges = {
    "SF_7"  : { "min_distance": 2200, "max_distance": 3700, "error_rate": 0.05, "decay" : 2},
    "SF_8"  : { "min_distance": 2400, "max_distance": 4300, "error_rate": 0.05, "decay" : 2},
    "SF_9"  : { "min_distance": 2600, "max_distance": 5200, "error_rate": 0.05, "decay" : 2},
    "SF_10" : { "min_distance": 3000, "max_distance": 6200, "error_rate": 0.05, "decay" : 2},
    "SF_11" : { "min_distance": 3500, "max_distance": 7400, "error_rate": 0.05, "decay" : 2},
    "SF_12" : { "min_distance": 4200, "max_distance": 9000, "error_rate": 0.05, "decay" : 2},
}

# returns the airtime of the packet in ms
def get_air_time(freq, spread, band, length, cr=5) -> int:

    # SF_1 doesn't exist and is for testing, handle it as SF 7
    if(spread == 1):
        SF = 7
    else:
        SF = spread

    symbol_duration = (2**SF) / (band)

    return math.ceil( (12 + 4.25 + 8 + math.ceil( (8*length - 4*SF +28)/(4*SF) )*cr )*symbol_duration )


def thread_function(nodes, bar, time):
    
    for i in range(0, time):
        bar.wait()
        for n in nodes:
            # print("updating %s" % n.name)
            n.update()

class world(object):

    def __init__(self, min_dist, max_dist, error_rate, decay):
        super().__init__()
        self.nodes : list[node] = []
        self.blocks = []
        self.time = 0

        # sun light intensity for solar panel charging
        self.weather = 0.4
        
        # override for LoRa transmission chart
        # print(min_dist)
        self.min_distance = min_dist
        self.max_distance = max_dist
        self.error_rate = error_rate
        self.decay = decay

    def add(self, node, x, y) -> None:
        node.position(x, y)
        node.logic.setup()
        self.nodes.append(node)
        node.register_in_world(self)

    def set_time(self, time):
        self.time = time

    def set_debugger(self, debug: debugger):
        self.debugger : debugger = debug

    def get_time(self):
        return self.time

    def get_nodes(self) -> list[node]:
        return self.nodes

    def get_weather(self):
        return self.weather

    def set_weather(self, weather):
        self.weather = weather

    def print_state(self):
        self.debugger.log("  Nodes:  %s" % str(len(self.nodes)).rjust(5))
        self.debugger.log("  Blocks: %s" % str(len(self.blocks)).rjust(5))
    
        label_arr : 'list[str]' = []
        entry_arr : 'list[str]' = []

        if(self.min_distance is None):
            label_arr.append("LoRa")
            entry_arr.append("")
        else:
            label_arr.append("custom")
            entry_arr.append(str(self.min_distance))

        if(self.max_distance is None):
            label_arr.append("LoRa")
            entry_arr.append("")
        else:
            label_arr.append("custom")
            entry_arr.append(str(self.max_distance))

        if(self.error_rate is None):
            label_arr.append("LoRa")
            entry_arr.append("")
        else:
            label_arr.append("custom")
            entry_arr.append(str(self.error_rate))

        if(self.decay is None):
            label_arr.append("LoRa")
            entry_arr.append("")
        else:
            label_arr.append("custom")
            entry_arr.append(str(self.decay))

        self.debugger.log("  %s %s %s %s" % ("tx_min".rjust(10), "tx_max".rjust(10), "tx_error".rjust(10), "decay".rjust(10)) )
        self.debugger.log("  %s %s %s %s" % (label_arr[0].rjust(10), label_arr[1].rjust(10), label_arr[2].rjust(10), label_arr[3].rjust(10)) )
        self.debugger.log("  %s %s %s %s" % (entry_arr[0].rjust(10), entry_arr[1].rjust(10), entry_arr[2].rjust(10), entry_arr[3].rjust(10)) )


    """
    Add node to the world at given position
    register the world with the transceiver
    """
    def add(self, node : node, x, y) -> None:
        node.position(x, y)
        node.logic.setup()
        self.nodes.append(node)
        node.get_transceiver().register_in_world(self)

    """
    Block transmissions from sender to receiver
    """
    def block_path(self, sender, receiver) ->  None:
        self.blocks.append((sender, receiver))

    """
    simulate the world for the specified time
    """
    def run(self, time):  
        for i in range(0, time):
            self.update()

    def update(self) -> None:

        for n in self.nodes:
            n.update()

        self.time += 1

    # get link quality for a packet (tx_packet) sent from sender to receiver
    def get_link_quality(self, sender : node, receiver : node, spread, tx_power) -> float:

        dist = np.sqrt( (sender.x - receiver.x)**2 + (sender.y - receiver.y)**2 )

        block = False
        for b in self.blocks:
            if(b[0] == sender.id and b[1] == receiver.id):
                block = True
                break
        if(block):
            return -2
        # no link between nodes

        # get distance from world_library
        # or use override
        if(self.min_distance is None):
            min_dist = transmission_ranges.get("SF_%s" % spread).get("min_distance")
        else:
            min_dist = self.min_distance

        if(self.max_distance is None):
            max_dist = transmission_ranges.get("SF_%s" % spread).get("max_distance")
        else:
            max_dist = self.max_distance

        if(self.error_rate is None):
            error_rate = transmission_ranges.get("SF_%s" % spread).get("error_rate")
        else:
            error_rate = self.error_rate

        if(self.decay is None):
            decay = transmission_ranges.get("SF_%s" % spread).get("decay")
        else:
            decay = self.decay

        power_fact = self.get_power_fact(tx_power)

        min_dist = min_dist * power_fact
        max_dist = max_dist * power_fact

        # only error_rate
        if(dist < min_dist):
            return 1.0-error_rate
        # decaying link quality
        elif(dist <= max_dist):
            start_exp = np.log(error_rate)
            fact = (dist - min_dist) / (max_dist - min_dist)
            return 1 - np.exp(start_exp*(1 -fact**decay) )
        # too far away
        else:
            return -1


    def get_power_fact(self, tx_power) -> float:
        
        # update distances based on tx_power
        # assume 20dB is max tx_power and linear range decrease
        if(tx_power < 20):
            power_fact = ((tx_power + ((13-tx_power) / 2.4  * np.abs((13-tx_power) / 7))) / 20 )
        else:
            power_fact = 1

        return power_fact

    # if transmission was successful
    # 1 = successful
    # 0 = not successful
    # -1 = out of range
    def successfull_transmission(self, sender, receiver, tx_packet) -> int:
        
        # return random.random() <= self.get_link_quality(sender, receiver, tx_packet)

        # more spread out for debugging lost packets
        link_quality = self.get_link_quality(sender, receiver, tx_packet.spreading_factor, tx_packet.tx_power)

        if(link_quality < 0):
            return -1
        else:
            if(random.random() <= link_quality):
                return 1
            else:
                # p = copy.copy(tx_packet)
                # self.debugger.add_destroyed_packet(destroyed_packet(
                #     p,
                #     sender.id,
                #     receiver.id,
                #     Destruction_type.WORLD
                # ))
                return 0

        
    # simulate the transmission of the package to all nodes
    # ignore propagation time as it is irrelevant in the ms simulation steeps size
    # check distance and link quality to all nodes, then calculate if transmission was successful
    # add RSSI factor to rx_packet since all distance information is only on world
    # 
    # I dont like the repetition of code from @function successfull_transmission, but multiple return values also unclean
    def transmit_packet(self, sender, tx_packet) -> None:
        for n in self.nodes:
            if(not n is sender):
                trans_status = self.successfull_transmission(sender, n, tx_packet)
                if(trans_status >= 0):
                    rx_packet = copy.copy(tx_packet)
                    
                    # calc rssi
                    if(self.max_distance is None):
                        max_dist = transmission_ranges.get("SF_%s" % tx_packet.spreading_factor).get("max_distance")
                    else:
                        max_dist = self.max_distance
                     
                    dist = np.sqrt( (sender.x - n.x)**2 + (sender.y - n.y)**2 )
                    # calculate drop off in rssi
                    #       linear drop             + random jitter         penalty for worse antenna at sensor nodes
                    # rssi = dist/max_dist * -(120) + random.randint(-2, 2) - 10*(not hasattr(n.logic, 'local_db'))
                    rssi = dist/max_dist * -(120) - 10*(not hasattr(n.logic, 'local_db'))
                    
                    # set packet RSSI
                    rx_packet.set_rssi(rssi)
                    # notify transceiver of receiving node with corruption status
                    n.get_transceiver().receive(rx_packet, corrupted=(trans_status == 0) )
                    
                    self.debugger.log("receiving packet %s from %s @ node %s @ time %i" % (tx_packet.payload, tx_packet.sender, n.name, self.time), 4)                 

    def visualize_old(self):
        # x, y , -x, -y
        max_dim = [0, 0, 0, 0]

        # get dimensions for landscape
        for n in self.nodes:

            if(n.x > max_dim[0]):
                max_dim[0] = n.x

            if(n.y > max_dim[1]):
                max_dim[1] = n.y

            if(n.x < max_dim[3]):
                max_dim[2] = n.x
            
            if(n.y < max_dim[3]):
                max_dim[3] = n.y

        fig, ax = plt.subplots()

        fig.set_figheight(10)
        fig.set_figwidth(16)

        ax.set_xlim(max_dim[2]-100, max_dim[0]+100)
        ax.set_ylim(max_dim[3]-100, max_dim[1]+100)

        # for establishing the arrows
        # (n.x n.y cn.x cn.y)
        # double-sided
        # 1->2
        # 2<-1
        # quality
        arrows = []

        node_list = []
        for n in self.nodes:
            node_list.append(n)
            for cn in self.nodes:

                if(not cn in node_list):
                    
                    # print("%s:   %i %i" % (n.name, n.x, n.y))

                    one_two = self.get_link_quality(n, cn, n.get_transceiver().get_spreading_factor(), n.get_transceiver().get_tx_power())
                    two_one = self.get_link_quality(cn, n, cn.get_transceiver().get_spreading_factor(), cn.get_transceiver().get_tx_power())
                    
                    if(one_two > 0 and two_one > 0):
                        quali = one_two
                        double_sided = True
                    elif(one_two > 0):
                        quali = one_two
                        double_sided = False
                    elif(two_one > 0):
                        quali = two_one
                        double_sided = False
                    else:
                        quali = 0.0           

                    if(quali > 0):
                        arrows.append([
                            (n.x, n.y, cn.x, cn.y),
                            double_sided,
                            one_two > 0,
                            two_one > 0,
                            quali
                        ])

        # calc biggest dimension
        x_dim = max_dim[0]+100 - (max_dim[2]-100)
        y_dim = max_dim[1]+100 - (max_dim[3]-100)

        # percentage of display size of the circle
        circle_size = 0.02

        # also calculate the effect of the figure size (w=16, h=10)
        x_size = x_dim*circle_size* (10/16)
        y_size = y_dim*circle_size

        for n in self.nodes:
            
            if(type(n) is node_sensor):
                ax.add_patch(patches.Ellipse((n.x, n.y), x_size, y_size, color='g') )
            else:
                ax.add_patch(patches.Ellipse((n.x, n.y), x_size, y_size, color='r') )
            
            #ax.annotate("%s" % n.name, (n.x-45, n.y-45), fontsize=8)
            ax.text(n.x, n.y - (y_size*1.1), "%s" % n.name, rotation=0 , fontsize=8, ha='center')

        for arr in arrows:
            # print(arr)

            if(arr[4] > 0):

                theta_radians = math.atan2(arr[0][3] - arr[0][1], arr[0][2] - arr[0][0])

                x_arr_start = arr[0][0] + 0.5*x_size*math.cos(theta_radians)
                y_arr_start = arr[0][1] + 0.5*y_size*math.sin(theta_radians)

                x_arr_end = arr[0][2] - 0.5*x_size*math.cos(theta_radians)
                y_arr_end = arr[0][3] - 0.5*y_size*math.sin(theta_radians)

                x_arr = arr[0][2] - arr[0][0] - x_size*math.cos(theta_radians)
                y_arr = arr[0][3] - arr[0][1] - x_size*math.sin(theta_radians)


                if(arr[1]):
                    arr_style = '<->'
                elif(arr[2]):
                    arr_style = '->'
                else:
                    arr_style = '<-'

                ax.add_patch(patches.FancyArrowPatch(
                        (x_arr_start, y_arr_start),
                        (x_arr_end, y_arr_end),
                        arrowstyle=arr_style,
                        mutation_scale=15
                    ))

                rot_angle = (360.0 / (math.pi * 2) * theta_radians)
                if(np.abs(rot_angle) > 90):
                    rot_angle += 180

                # ax.text(x_arr_start+0.5*x_arr + 5*math.sin(theta_radians), y_arr_start+0.5*y_arr+ 5*math.cos(theta_radians), "%.2f" % (arr[4]), rotation= rot_angle , fontsize=8, ha='center', va='center')  
                ax.text(x_arr_start+0.5*x_arr + x_dim*(10/16)*0.01*math.sin(theta_radians), y_arr_start+0.5*y_arr+ y_dim*0.01*math.cos(theta_radians), "%.2f" % (arr[4]), rotation= rot_angle , fontsize=8, ha='center', va='center')  

        plt.show()

    def visualize(self):
        # x, y , -x, -y
        max_dim = [0, 0, 0, 0]

        # get dimensions for landscape
        for n in self.nodes:

            if(n.x > max_dim[0]):
                max_dim[0] = n.x

            if(n.y > max_dim[1]):
                max_dim[1] = n.y

            if(n.x < max_dim[3]):
                max_dim[2] = n.x
            
            if(n.y < max_dim[3]):
                max_dim[3] = n.y

        fig, ax = plt.subplots()

        fig.set_figheight(10)
        fig.set_figwidth(16)

        ax.set_xlim(max_dim[2]-100, max_dim[0]+100)
        ax.set_ylim(max_dim[3]-100, max_dim[1]+100)

        # for establishing the arrows
        # (n.x n.y cn.x cn.y)
        # double-sided
        # 1->2
        # 2<-1
        # quality
        arrows = []

        node_list = []
        for n in self.nodes:
            node_list.append(n)
            for cn in self.nodes:

                if(not cn in node_list):
                    
                    # print("%s:   %i %i" % (n.name, n.x, n.y))

                    one_two = self.get_link_quality(n, cn, n.get_transceiver().get_spreading_factor(), n.get_transceiver().get_tx_power())
                    two_one = self.get_link_quality(cn, n, cn.get_transceiver().get_spreading_factor(), cn.get_transceiver().get_tx_power())
                    
                    if(one_two > 0 and two_one > 0):
                        quali = one_two
                        double_sided = True
                    elif(one_two > 0):
                        quali = one_two
                        double_sided = False
                    elif(two_one > 0):
                        quali = two_one
                        double_sided = False
                    else:
                        quali = 0.0
                        double_sided = False           

                    arrows.append([
                        (n.x, n.y, cn.x, cn.y),
                        double_sided,
                        one_two > 0,
                        two_one > 0,
                        quali
                    ])

        # calc biggest dimension
        x_dim = max_dim[0]+100 - (max_dim[2]-100)
        y_dim = max_dim[1]+100 - (max_dim[3]-100)

        # percentage of display size of the circle
        circle_size = 0.02

        # arrow radius curvature
        arr_radius = 0.7

        # size of tikz figure
        target_width = 14
        target_height = 7

        # also calculate the effect of the figure size (w=16, h=10)
        x_size = x_dim*circle_size* (10/16)
        y_size = y_dim*circle_size

        for n in self.nodes:
            
            if(type(n) is node_sensor):
                ax.add_patch(patches.Ellipse((n.x, n.y), x_size, y_size, color='g') )
            else:
                ax.add_patch(patches.Ellipse((n.x, n.y), x_size, y_size, color='r') )
            
            #ax.annotate("%s" % n.name, (n.x-45, n.y-45), fontsize=8)
            ax.text(n.x, n.y - (y_size*1.1), "%s" % n.name, rotation=0 , fontsize=8, ha='center')


        odd = True
        tex_arrows = []

        for arr in arrows:
            # print(arr)

            if(arr[4] > 0):

                theta_radians = math.atan2(arr[0][3] - arr[0][1], arr[0][2] - arr[0][0])

                x_arr_start = arr[0][0] + 0.5*x_size*math.cos(theta_radians)
                y_arr_start = arr[0][1] + 0.5*y_size*math.sin(theta_radians)

                x_arr_end = arr[0][2] - 0.5*x_size*math.cos(theta_radians)
                y_arr_end = arr[0][3] - 0.5*y_size*math.sin(theta_radians)

                x_arr = arr[0][2] - arr[0][0] - x_size*math.cos(theta_radians)
                y_arr = arr[0][3] - arr[0][1] - x_size*math.sin(theta_radians)


                if(arr[1]):
                    arr_style = '<->'
                    tex_arrow_style = 'stealth-stealth'
                elif(arr[2]):
                    arr_style = '->'
                    tex_arrow_style = '-stealth'
                else:
                    arr_style = '<-'
                    tex_arrow_style = 'stealth-'
                
                tex_offset = 1.8

                if(odd):
                    con_style = "arc3,rad=%.2f" % arr_radius
                    tex_arrows.append(r"\draw[%s,draw=black] (axis cs:%.2f,%.2f) to [out=%.2f,in=%.2f] (axis cs:%.2f,%.2f);" % (tex_arrow_style, x_arr_start, y_arr_start, -math.degrees(math.atan(arr_radius))*tex_offset, -180 + math.degrees(math.atan(arr_radius))*tex_offset , x_arr_end, y_arr_end))
                else:
                    con_style = "arc3,rad=-%.2f" % arr_radius
                    tex_arrows.append(r"\draw[%s,draw=black] (axis cs:%.2f,%.2f) to [out=%.2f,in=%.2f] (axis cs:%.2f,%.2f);" % (tex_arrow_style, x_arr_start, y_arr_start, math.degrees(math.atan(arr_radius))*tex_offset, 180 - math.degrees(math.atan(arr_radius))*tex_offset, x_arr_end, y_arr_end))

                ax.add_patch(patches.FancyArrowPatch(
                        (x_arr_start, y_arr_start),
                        (x_arr_end, y_arr_end),
                        arrowstyle=arr_style,
                        mutation_scale=15,
                        connectionstyle=con_style
                    ))


                rot_angle = (360.0 / (math.pi * 2) * theta_radians)
                if(np.abs(rot_angle) > 90):
                    rot_angle += 180

                # ax.text(x_arr_start+0.5*x_arr + 5*math.sin(theta_radians), y_arr_start+0.5*y_arr+ 5*math.cos(theta_radians), "%.2f" % (arr[4]), rotation= rot_angle , fontsize=8, ha='center', va='center')  
                # ax.text(x_arr_start+0.5*x_arr + x_dim*(10/16)*0.01*math.sin(theta_radians), y_arr_start+0.5*y_arr+ y_dim*0.01*math.cos(theta_radians), "%.2f" % (arr[4]), rotation= rot_angle , fontsize=8, ha='center', va='center')  
                
                dim_fact = y_dim / x_dim
                arr_length = np.sqrt( (x_arr)**2 + (y_arr)**2 )

                off_fact_y = 0.86
                off_fact_x = 0.35       

                if(odd):
                    # print("odd")
                    # print(x_arr > 0)
                    # print(y_arr > 0)

                    # print("x_arr_start: %.1f    x_arr_end: %.1f" % (x_arr_start, x_arr_end))
                    # print("y_arr_start: %.1f    y_arr_end: %.1f" % (y_arr_start, y_arr_end))
                    # print("x_arr: %.1f" % x_arr)
                    # print("y_arr: %.1f" % y_arr)
                    # print("theta: %.1f" % math.degrees(theta_radians))

                    # print("text_x_off: %.2f" % (- ( off_fact_x*arr_radius*(1/dim_fact)*arr_length + x_dim*(10/16)*0.01*math.sin(theta_radians))*math.sin(theta_radians)) )
                    # print("text_y_off: %.2f" % (- ( off_fact_y*arr_radius*dim_fact*arr_length + y_dim*0.012*math.cos(theta_radians))*math.cos(theta_radians)) )
                    
                    text_x = x_arr_start+0.5*x_arr + ( off_fact_x*arr_radius*(1/dim_fact)*arr_length + x_dim*(10/16)*0.01*math.sin(theta_radians))*math.sin(theta_radians) 
                    text_y = y_arr_start+0.5*y_arr - ( off_fact_y*arr_radius*dim_fact*arr_length + y_dim*0.012*math.cos(theta_radians))*math.cos(theta_radians) 
                else:
                    # print(x_arr > 0)
                    # print(y_arr > 0)

                    # print("x_arr_start: %.1f    x_arr_end: %.1f" % (x_arr_start, x_arr_end))
                    # print("y_arr_start: %.1f    y_arr_end: %.1f" % (y_arr_start, y_arr_end))
                    # print("x_arr: %.1f" % x_arr)
                    # print("y_arr: %.1f" % y_arr)
                    # print("theta: %.1f" % math.degrees(theta_radians))

                    # print("text_x_off: %.2f" % ( ( off_fact_x*arr_radius*1/dim_fact*arr_length + x_dim*(10/16)*0.01*math.sin(theta_radians))*math.sin(theta_radians)))
                    # print("text_y_off: %.2f" % (( off_fact_y*arr_radius*dim_fact*arr_length + y_dim*0.01*math.cos(theta_radians))*math.cos(theta_radians) ))

                    text_x = x_arr_start+0.5*x_arr - ( off_fact_x*arr_radius*1/dim_fact*arr_length + x_dim*(10/16)*0.01*math.sin(theta_radians))*math.sin(theta_radians)
                    text_y = y_arr_start+0.5*y_arr + ( off_fact_y*arr_radius*dim_fact*arr_length + y_dim*0.01*math.cos(theta_radians))*math.cos(theta_radians) 
            
                ax.text(text_x, text_y, "%.2f" % (arr[4]), rotation= rot_angle , fontsize=8, ha='center', va='center')  

            odd = not odd

        ax.set_xlabel(r"$x$ in m")
        ax.set_ylabel(r"$y$ in m")
        tikzplotlib.save(str(Path(__file__).parent.parent) + "/results/world_vis.tex", encoding="utf-8")

        # post processing to transform to scale and add cureved arrows

        reading_file = open(str(Path(__file__).parent.parent) + "/results/world_vis.tex", "r")

        arrow_cnt = 0

        new_file_content = ""
        for line in reading_file:
            stripped_line = line.strip()

            new_line = stripped_line

            if(stripped_line.__contains__("ellipse")):
                split_line = stripped_line.split("ellipse ")
                numbers = re.findall('-?\d+\.?\d*', split_line[-1])
                el_x = float(numbers[0])
                el_y = y_dim/x_dim * target_width/target_height * el_x
                new_line = split_line[0] + ( "ellipse (%.2f and %.2f);" % (el_x, el_y) )

            elif(stripped_line.__contains__("<->")):
                new_line = tex_arrows[arrow_cnt]
                arrow_cnt+=1

            elif(stripped_line.__contains__("_")):
                new_line = stripped_line.replace("_", "")

            new_file_content += new_line +"\n"

        reading_file.close()

        writing_file = open(str(Path(__file__).parent.parent) + "/results/world_vis.tex", "w")
        writing_file.write(new_file_content)
        writing_file.close()

        plt.show()