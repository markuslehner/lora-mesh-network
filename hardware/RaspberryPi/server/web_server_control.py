from flask import Flask, render_template, request
from lib.packet_handler import packet_handler
import threading
import time
import logging
from datetime import datetime

from werkzeug.serving import make_server

# drawing stuff
import io
import base64

import networkx as nx
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from lib.command import request_command, reset_command, ack_command, nack_command, set_interval_command, ack_join_command
from lib.packet import Command_type


app : Flask= Flask(__name__)

# positions of Nodes
pos = None

# count of routes to 
route_cnt = 0

#include join paths
include_join_path = True

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server(host='0.0.0.0', port=5001, app=app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

def thread_function():
    while True:
        time.sleep(2.5)

def create_webserver(name : str, packet_ha : packet_handler, disable_logging : bool):

    app : Flask= Flask(name)

    my_packet_handler : packet_handler = packet_ha

    @app.route('/')
    def index():

        # create node list
        nodes = []

        for i in range(my_packet_handler.num_connected_nodes):
            nodes.append([
                my_packet_handler.node_ids[i],
                my_packet_handler.node_distances[i],
                my_packet_handler.node_battery_level[i]
            ])

        # create picture graph
        # organize nodes

        G = nx.Graph()
        G.add_node(my_packet_handler.id)

        global include_join_path
        for n in range(len(my_packet_handler.node_ids)):
            G.add_node(my_packet_handler.node_ids[n])
            if(include_join_path): G.add_edge(my_packet_handler.node_ids[n], my_packet_handler.node_of_first_contact[n])
        
        global pos
        if(pos is None or my_packet_handler.num_connected_nodes != len(pos) - 1 or route_cnt != len(my_packet_handler.routes)):
            pos = nx.spring_layout(G)

        fig = Figure()
        axis = fig.add_subplot(1, 1, 1)
        axis.set_title("Graph representation of Network")

        val_map = {my_packet_handler.id: 0.9}
        values = [val_map.get(node, 0.2) for node in G.nodes()]

        nx.draw(G, ax=axis, pos=pos, node_color=values, with_labels=True, font_weight='bold', cmap = plt.cm.get_cmap('rainbow'), vmin=0, vmax=1)

        # Convert plot to PNG image
        pngImage = io.BytesIO()
        FigureCanvas(fig).print_png(pngImage)
        
        # Encode PNG image to base64 string
        pngImageB64String = "data:image/png;base64,"
        pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

        return render_template('command_center.html', 
                                num_nodes=my_packet_handler.num_connected_nodes, 
                                nodes=nodes, image=pngImageB64String, 
                                interval="%.1f min" % ( my_packet_handler.interval/1000/60 ),
                                interval_active = "%.2f" % ( 100 * (my_packet_handler.num_connected_nodes*my_packet_handler.interval_slot_width + my_packet_handler.interval_active_extension) / my_packet_handler.interval ),
                                nodes_sending=my_packet_handler.nodes_started_sending,
                                all_nodes_sending = my_packet_handler.all_nodes_sending,
                                nodes_sleeping = my_packet_handler.nodes_sleeping,
                                started_successfully = my_packet_handler.successfully_started,
                                network_running = my_packet_handler.network_running,
                                new_nodes = my_packet_handler.new_nodes_to_join,
                                command_list = my_packet_handler.command_center.get_commands_for_website()
                                )

    
    @app.route('/network_overview')
    def network_overview():
        G = nx.Graph()
        G.add_node(my_packet_handler.id)

        global include_join_path
        for n in range(len(my_packet_handler.node_ids)):
            G.add_node(my_packet_handler.node_ids[n])
            if(include_join_path): G.add_edge(my_packet_handler.node_ids[n], my_packet_handler.node_of_first_contact[n])
        
        for route in my_packet_handler.routes:
            for i in range(len(route)-1):
                G.add_edge(route[i], route[i+1])

        global pos
        global route_cnt
        if(pos is None or my_packet_handler.num_connected_nodes != len(pos) - 1 or route_cnt != len(my_packet_handler.routes)):
            pos = nx.spring_layout(G)
            route_cnt = len(my_packet_handler.routes)


        fig = Figure()
        axis = fig.add_subplot(1, 1, 1)
        axis.set_title("Graph representation of Network")

        val_map = {my_packet_handler.id: 0.9}
        values = [val_map.get(node, 0.2) for node in G.nodes()]

        nx.draw(G, ax=axis, pos=pos, node_color=values, with_labels=True, font_weight='bold', cmap = plt.cm.get_cmap('rainbow'), vmin=0, vmax=1)

        # Convert plot to PNG image
        pngImage = io.BytesIO()
        FigureCanvas(fig).print_png(pngImage)
        
        # Encode PNG image to base64 string
        pngImageB64String = "data:image/png;base64,"
        pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

        return render_template('network_overview.html', image= pngImageB64String, include_join_path=str(include_join_path))

    @app.route('/statistics')
    def statistics():
        return render_template('statistics.html',
                                time_started=datetime.fromtimestamp(my_packet_handler.time_started/1000).strftime("%m-%d %H:%M:%S") if my_packet_handler.time_started != 0 else "never",
                                time_restarted=datetime.fromtimestamp(my_packet_handler.time_restarted/1000).strftime("%m-%d %H:%M:%S") if my_packet_handler.time_restarted != 0 else "never",
                                num_rx=my_packet_handler.num_rx_after_start,
                                num_tx=my_packet_handler.num_tx_after_start,
                                num_req=my_packet_handler.num_not_received_on_first_try,
                                pdr="%.2f%%" % (my_packet_handler.num_rx_after_start/my_packet_handler.num_tx_after_start * 100.0) if my_packet_handler.num_tx_after_start > 0 else "-",
                                num_rejoins=my_packet_handler.num_joins - my_packet_handler.num_connected_nodes
                                )

    @app.route('/about')
    def about():
        return render_template('about.html')

    # function calls
    @app.route('/queue_command', methods=['POST'])
    def queue_command():
        data = request.form

        # print("QUEUEING COMMAND")
        # print("  %s : %s" % ("TYPE".rjust(10), str(data.get("type")).rjust(20) ))
        # print("  %s : %s" % ("TARGET".rjust(10), str(data.get("target")).rjust(20) ))
        # print("  %s : %s" % ("PRIO".rjust(10), str(data.get("prio")).rjust(20) ))
        # print("  %s : %s" % ("ACK".rjust(10), str(data.get("ack")).rjust(20) ))
        # print("  %s : %s" % ("BROADC.".rjust(10), str(data.get("broadcast")).rjust(20) ))
        # print("  %s : %s" % ("DIST.".rjust(10), str(data.get("distance")).rjust(20) ))
        # print("  %s : %s" % ("BLOCK".rjust(10), str(data.get("block_node")).rjust(20) ))

        target : int = int(data.get("target"))
        ack : bool = data.get("ack") == "true"
        prio : int = int(data.get("prio"))
        distance : int = int(data.get("distance"))
        block_node : int = int(data.get("block_node"))

        if(data.get("type") == "remove_node"):
            my_packet_handler.remove_node(target)
            command_t : Command_type = None
        else:
            command_t : Command_type = Command_type.from_str(data.get("type"))

        if( data.get("broadcast") == "true" ):
            target = 0

        if(command_t is None):
            pass
        elif(command_t == Command_type.RESET):
            my_packet_handler.command_center.register_command(
                reset_command(target),
                prio=1
            )
        elif(command_t == Command_type.REQUEST):
            my_packet_handler.command_center.register_command(
                request_command(target)
                )
        elif(command_t == Command_type.SET_INTERVAL):
            my_packet_handler.command_center.register_command(
                set_interval_command(
                            target,
                            prio=prio,
                            retry_sending=True,
                            one_interval=True
                ))
        elif(command_t == Command_type.JOIN_ACK):
            my_packet_handler.command_center.register_command(
                ack_join_command(
                            target,
                            1 if (not target in my_packet_handler.node_ids) else my_packet_handler.node_distances[my_packet_handler.node_ids.index(target)],
                            my_packet_handler.id,
                            prio=prio
                ))
        else:
            payload = None

            if(command_t == Command_type.SET_BLOCK or command_t == Command_type.REMOVE_BLOCK):
                payload = int(block_node).to_bytes(1, 'little')
            elif(command_t == Command_type.SET_DISTANCE):
               payload = int(distance).to_bytes(1, 'little')

            if(ack):
                my_packet_handler.command_center.register_command(
                    ack_command(target, command_t, payload=payload),
                    prio=prio
                )
            else:
                my_packet_handler.command_center.register_command(
                    nack_command(target, command_t, payload=payload),
                    prio=prio
                )

        return ("nothing")

    # function calls
    @app.route('/set_include_join_path', methods=['POST'])
    def set_include_join_path():
        data = request.form

        global include_join_path
        include_join_path = data.get("include_join_path") == "true"
        print("setting include_join_path to %s", include_join_path)

        return ("nothing")

    # function calls
    @app.route('/reset_routes', methods=['POST'])
    def reset_routes():

        my_packet_handler.routes = []
        print("Resetting routes")

        return ("nothing")

    my_thread = threading.Thread(target=thread_function)
    my_thread.daemon = True
    my_thread.start()

    # disable logging
    if(disable_logging):
        log = logging.getLogger('werkzeug')
        log.disabled = True
        app.logger.disabled = True

    server = ServerThread(app)
    server.daemon = True
    server.start()
