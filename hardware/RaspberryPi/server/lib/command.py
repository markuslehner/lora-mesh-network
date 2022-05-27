from lib.packet import packet, Payload_type, Command_type
import struct

class command(object):
    def __init__(self, node : int =None, prio : int =2, retry_sending : bool = False, one_interval : bool= True, payload = None) -> None:
        super().__init__()

        # if it should be retried to send the 
        # command if it is still valid (one or more intervals) and has not been marked as finished
        self.retry : bool = retry_sending
        # priority of command
        self.priority : int = prio
        # the node id that this command is concerning
        self.node_id = node
        # if the command is valid for only one interval
        self.one_interval = one_interval
        # the type of the command
        self.type : Command_type = None
        # if the command is finished
        self.finished = False
        # payload of command
        self.payload = payload
        # packet_id of the last packet with this command to trace ACK commands
        self.packet_id = None

        # how often the command was sent
        self.send_cnt = 0


    def set_prio(self, prio: int):
        self.priority = prio

    def get_packet(self) -> packet:
        self.send_cnt += 1

        pay_type : Payload_type = Payload_type.COMMAND
        payl : bytes= self.type.value.tobytes()

        if(not self.payload is None):
            payl += self.payload

        if(self.type == Command_type.ACK):
            pay_type = Payload_type.ACK
            payl = None
        elif(isinstance(self, ack_command)):
            pay_type = Payload_type.COMMAND_ACK

        return packet(
                0,
                0,
                self.node_id,
                10,
                0,                   
                0,
                False,
                pay_type,
                payl
            )

    def update(self, packet, packet_handler) -> None:
        pass

    def is_finished(self) -> bool:
        return self.finished

    def has_started(self) -> bool:
        return self.send_cnt > 0

    def triggers_response(self) -> bool:
        return False

    def only_one_interval(self) -> bool:
        return self.one_interval

    def retry_sending(self) -> bool:
        return self.retry

    def set_packet_id(self, packet_id : int) -> None:
        self.packet_id = packet_id

    def prepare_sending(self, packet_handler, command_center) -> None:
        if(self.type == Command_type.START_SENDING or self.type == Command_type.STOP_SENDING):
            status = self.type == Command_type.START_SENDING

            if(self.node_id == 0):
                for i in range(packet_handler.num_connected_nodes):
                    packet_handler.node_sending_status[i] = status
            else:
                idx = packet_handler.node_ids.index(self.node_id)
                packet_handler.node_sending_status[idx] = status

        elif(self.type == Command_type.SET_DISTANCE):
            idx = packet_handler.node_ids.index(self.node_id)
            packet_handler.node_distances[idx] = int.from_bytes(self.payload, "little")

        elif(self.type == Command_type.ENABLE_SLEEP):
            if(self.node_id == 0):
                for i in range(packet_handler.num_connected_nodes):
                    packet_handler.node_sleeping_status[i] = True
                    packet_handler.node_wanted_sleeping_status[i] = True
            else:
                idx = packet_handler.node_ids.index(self.node_id)
                packet_handler.node_sleeping_status[idx] = True
                packet_handler.node_wanted_sleeping_status[idx] = True

        elif(self.type == Command_type.DISABLE_SLEEP):
            if(self.node_id == 0):
                for i in range(packet_handler.num_connected_nodes):
                    packet_handler.node_sleeping_status[i] = False
                    packet_handler.node_wanted_sleeping_status[i] = False
            else:
                idx = packet_handler.node_ids.index(self.node_id)
                packet_handler.node_sleeping_status[idx] = False
                packet_handler.node_wanted_sleeping_status[idx] = False

    def get_status(self) -> str:
            if(self.is_finished()):
                return "finished"
            elif(self.send_cnt > 0):
                if(self.retry):
                    return "retry"
                else:
                    return "sent"
            else:
                return "queued"

    def __str__(self) -> str:
        if(self.node_id == 0):
            return "%s to all nodes" % str(self.type)
        else:
            return "%s to node %i" % ( str(self.type), self.node_id)

class request_command(command):
    def __init__(self, node : int, prio = 2, retry_sending = False, one_interval = True):
        super().__init__(node, prio, retry_sending, one_interval)
        self.type : Command_type = Command_type.REQUEST

    def update(self, packet : packet, packet_handler):
        if(packet.payload_type == Payload_type.DATA):
            self.finished = True

    def triggers_response(self) -> bool:
        return True

class reset_command(command):
    def __init__(self, node : int, prio = 2, retry_sending = False, one_interval = False):
        super().__init__(node, prio, retry_sending, one_interval)

        self.finished = False
        self.type : Command_type = Command_type.RESET

    def prepare_sending(self, packet_handler, command_center) -> None:
        command_center.remove_commands_for_node(self.node_id)

    def update(self, packet : packet, packet_handler):
        if(packet.payload_type == Payload_type.JOIN):
            self.finished = True

    def triggers_response(self) -> bool:
        return False

class ack_join_command(command):
    def __init__(self, node : int, node_dist : int, central_id , prio = 1, retry_sending = False, one_interval = True):
        super().__init__(node, prio, retry_sending, one_interval)
        self.node_dist : int = node_dist
        self.central_id = central_id
        self.type : Command_type = Command_type.JOIN_ACK

    def prepare_sending(self, packet_handler, command_center) -> None:
        
        # plausibilit check
        # should alwsays be fulfilled
        if(self.node_id != 0 and self.node_id in packet_handler.node_ids):
            packet_handler.remove_received_join_requests(self.node_id)

    def triggers_response(self) -> bool:
        return False

    def get_packet(self) -> packet:
        self.send_cnt += 1
        self.finished = True
        return packet(
                0,
                0,
                self.node_id,
                10,
                0,                   
                0,
                False,
                Payload_type.JOIN_ACK,
                int(self.central_id).to_bytes(1, 'little') + int(self.node_dist).to_bytes(1, 'little')
            )

    def __str__(self) -> str:
        return "ACK_JOIN to node %i for dist: %i" % ( self.node_id, self.node_dist)

class set_interval_command(command):
    def __init__(self, node : int, prio = 1, retry_sending = False, one_interval = True):
        super().__init__(node, prio, retry_sending, one_interval)
        self.type : Command_type = Command_type.SET_INTERVAL

    def update(self, packet : packet, packet_handler):
        if(packet.payload_type == Payload_type.ACK and int.from_bytes(packet.payload, "little") == self.packet_id):

            idx = packet_handler.node_ids.index(self.node_id)
            packet_handler.node_interval_ack[idx] = True

            # set sending status for nodes rejoining
            if(self.payload[16] == 255):
                packet_handler.node_sending_status[idx] = True

            self.finished = True

    def triggers_response(self) -> bool:
        return True

    def prepare_sending(self, packet_handler, command_center):
        next_interval_start_node = packet_handler.next_interval_start - packet_handler.get_time()

        idx = packet_handler.node_ids.index(self.node_id)
        packet_handler.node_interval_sent[idx] = True

        self.payload = int(packet_handler.interval).to_bytes(4, 'little')
        self.payload += int(packet_handler.num_connected_nodes*packet_handler.interval_slot_width + packet_handler.interval_active_extension).to_bytes(4, 'little')
        self.payload += int(idx*packet_handler.interval_slot_width).to_bytes(4, 'little')
        self.payload += int(next_interval_start_node).to_bytes(4, 'little')
        self.payload += int(packet_handler.nodes_started_sending*255).to_bytes(1, 'little')  
    
    def __str__(self) -> str:
        return "%s with: time_to_next: %i" % (super().__str__(), struct.unpack('<i', self.payload[12:16])[0] )

class resync_interval_command(command):
    def __init__(self, node : int, prio = 1, retry_sending = False, one_interval = True):
        super().__init__(node, prio, retry_sending, one_interval)
        self.type : Command_type = Command_type.RESYNC_INTERVAL

    def update(self, packet : packet, packet_handler):
        if(packet.payload_type == Payload_type.ACK and int.from_bytes(packet.payload, "little") == self.packet_id):
            self.finished = True

    def triggers_response(self) -> bool:
        return False

    def prepare_sending(self, packet_handler, command_center):
        next_interval_start_node = packet_handler.next_interval_start - packet_handler.get_time()
        self.payload = int(next_interval_start_node).to_bytes(4, 'little')
    
    def __str__(self) -> str:
        return "%s with: time_to_next: %i" % (super().__str__(), struct.unpack('<i', self.payload[0:4])[0] )

class ack_command(command):
    def __init__(self, node : int, com_t : Command_type, prio = 3, retry_sending = False, one_interval = False, payload = None):
        super().__init__(node, prio, retry_sending, one_interval, payload)
        self.type : Command_type = com_t

    def update(self, packet : packet, packet_handler):
        if(packet.payload_type == Payload_type.ACK and int.from_bytes(packet.payload, "little") == self.packet_id):
            self.finished = True

    def triggers_response(self) -> bool:
        return True

class nack_command(command):
    def __init__(self, node : int, com_t : Command_type, prio = 3, retry_sending = False, one_interval = False, payload = None):
        super().__init__(node, prio, retry_sending, one_interval, payload)
        self.type : Command_type = com_t

    def is_finished(self) -> bool:
        return self.has_started()

    def triggers_response(self) -> bool:
        return False

    