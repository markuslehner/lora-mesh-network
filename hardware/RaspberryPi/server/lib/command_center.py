import numpy as np
from lib.command import command
from lib.logger import logger

from lib.packet import packet
from lib.packet import Command_type
# from lib.packet_handler import packet_handler

class command_center(object):

    def __init__(self, appID : int, node_id : int, packet_handler, debugger : logger) -> None:
        super().__init__()

        # app id
        self.app_id : int = appID
        # node id of central node
        self.node_id : int = node_id
        # logic central that the command enter is connected to
        self.logic = packet_handler
        # connection to debugger
        self.debugger = debugger

        '''UPDATE PARAMS'''
        self.started_updating = False
        self.interval_queue_update = 1000*5
        self.last_queue_update = 0

        '''COMMAND UPDATING'''
        # list of intervals that have been sent this interval
        self.commands_sent_this_interval : 'list[command]' = []

        # number of update intervals until next sending
        self.updates_until_send = 0

        # list of commands that should be sent this interval
        # sorted by priority
        self.commands_to_be_sent : 'list[command]'= []

        # command list of all active commands
        self.command_list : 'list[command]' = []

        # store last_interval time to differentiate between intervals
        self.start_of_this_interval = 0

    def register_command(self, command : command, prio : int = None):

        if( not prio is None):
            command.set_prio(prio)

        self.command_list.append(command)

    def update(self):

        # start updating
        start_updating = False
        if(self.logic.nodes_started_sending):
            # start updating after the sending time of nodes has passed
            # and self.logic.last_interval_start + self.logic.interval_slot_width*self.logic.num_connected_nodes + self.logic.interval_active_extension > self.get_time()
            if(not self.started_updating and self.logic.last_interval_start != self.start_of_this_interval and self.logic.last_interval_start + self.logic.interval_slot_width*self.logic.num_connected_nodes < self.get_time()):
                start_updating = True
        else:
            # use whole interval
            if(not self.started_updating and self.logic.last_interval_start != self.start_of_this_interval):
                start_updating = True

        if(start_updating):    
            self.started_updating = True
            self.debugger.log("  CC: START UPDATING", 2)

            self.commands_to_be_sent = sorted(self.command_list, key=lambda x: x.priority)
        
        # update
        if(self.started_updating):
             if(self.get_time() - self.last_queue_update > self.interval_queue_update - 1):
                self.last_queue_update = self.get_time()
                self.debugger.log("  CC: UPDATING", 4)

                if(self.updates_until_send > 0):
                    self.updates_until_send -= 1
                
                if(self.updates_until_send == 0):
                    next_command = self.get_next_command()
                    if(next_command is None):
                        # reshedule unfinished commands
                        for c in self.command_list:
                            if(not c.is_finished()):
                                self.commands_to_be_sent.append(c)

                        self.commands_to_be_sent.sort(key=lambda x: x.priority)
                        # get first command
                        next_command = self.get_next_command()

                    if(not next_command is None):
                        # send the command
                        self.updates_until_send = 1 + next_command.triggers_response()
                        next_command.prepare_sending(self.logic, self)
                        self.send_command(next_command)
                        self.commands_sent_this_interval.append(next_command)

        # stop updating
        end_updating = False
        if(self.logic.nodes_sleeping):
            # use only active time
            if(self.started_updating and self.logic.last_interval_start + self.logic.interval_slot_width*self.logic.num_connected_nodes + self.logic.interval_active_extension < self.get_time()):
                end_updating = True
        else:
            # use all remaining interval, except buffer of 20s
            if(self.started_updating and self.logic.next_interval_start - 5000 < self.get_time()):
                end_updating = True
        
        if(end_updating):

                self.started_updating = False
                self.commands_sent_this_interval = []
                self.commands_to_be_sent = []
                self.updates_until_send = 0

                self.start_of_this_interval = self.logic.last_interval_start

                # remove finished and expired commands 
                remove = []
                for c in range(len(self.command_list)):
                    if(self.command_list[c].is_finished() or self.command_list[c].only_one_interval()):
                        remove.append(c)
                
                for i in range(len(remove)):
                    self.command_list.pop(remove[i] - i)

                self.debugger.log("  CC: END UPDATING", 2)

    def get_next_command(self) -> command:
        if(len(self.commands_to_be_sent) > 0):
            # get first command and send it
            cur_command : command = self.commands_to_be_sent.pop(0)
            empty = False
            # get next command in list
            # check if it is also finished
            while(cur_command.is_finished() or ( cur_command.has_started() and not cur_command.retry_sending()) ):
                if(len(self.commands_to_be_sent) == 0):
                    empty = True
                    break
                else:
                    cur_command = self.commands_to_be_sent.pop(0)
            
            if(empty):
                return None
            else:
                return cur_command
        else:
            return None

    def remove_commands_for_node(self, nid : int, keep_types : 'list[Command_type]' = [Command_type.RESET]):
        self.debugger.log("  removing commands for node %i, keeping %s" % (nid, str(keep_types)), 3)
        self.commands_to_be_sent = [e for e in self.commands_to_be_sent if e.node_id != nid or e.is_finished() or e.type in keep_types]
        self.command_list = [e for e in self.command_list if e.node_id != nid or e.is_finished() or e.type in keep_types]

    def get_commands_for_website(self) -> list:
        commands = []

        for c in self.command_list:
            commands.append([str(c.type), c.node_id, c.get_status()])

        return commands

    def send_command(self, command : command):

        pkg : packet = command.get_packet()

        pkg.appID = self.app_id
        pkg.origin = self.node_id
        pkg.packet_id = self.logic.get_packet_id()

        # update command packet id
        command.set_packet_id(pkg.packet_id)

        self.debugger.log("  CC: Sending %s (pid:%i)" % (str(command), pkg.packet_id) )

        self.logic.queue_packet(pkg, -1)

    def handle_packet(self, packet):
        for c in self.commands_sent_this_interval:
            if(c.one_interval):
                if(not c.is_finished() and ( c.node_id == None or c.node_id == packet.origin) ):
                    c.update(packet, self.logic)

        for c in self.command_list:
            if(not c.one_interval and c.has_started()):
                if(not c.is_finished() and ( c.node_id == None or c.node_id == packet.origin) ):
                    c.update(packet, self.logic)

    def get_time(self) -> int:
        return self.logic.get_time() 