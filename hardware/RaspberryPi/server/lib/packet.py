from bitarray import bitarray
from enum import Enum

class Payload_type(Enum):

    # main types
    JOIN = bitarray('11110000')
    JOIN_ACK = bitarray('00001111')
    ACK = bitarray('11111111')
    DATA = bitarray('00000000')
    COMMAND = bitarray('10111101')
    COMMAND_ACK = bitarray('01000010')
    ROUTE = bitarray('01001101')

    def from_byte(pl_type):

        if(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.JOIN.value.tobytes()):
            return Payload_type.JOIN
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.JOIN_ACK.value.tobytes()):
            return Payload_type.JOIN_ACK
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.DATA.value.tobytes()):
            return Payload_type.DATA
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.ACK.value.tobytes()):
            return Payload_type.ACK
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.COMMAND.value.tobytes()):
            return Payload_type.COMMAND
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.ROUTE.value.tobytes()):
            return Payload_type.ROUTE
        else:
            return Payload_type.DATA
    
    def __str__(self) -> str:
        if(self == Payload_type.DATA):
            return "DATA"
        elif(self == Payload_type.JOIN):
            return "JOIN"
        elif(self == Payload_type.JOIN_ACK):
            return "JOIN_ACK"
        elif(self == Payload_type.ACK):
            return "ACK"
        elif(self == Payload_type.COMMAND):
            return "COMMAND"
        elif(self == Payload_type.ROUTE):
            return "ROUTE"

        return "UNKNOWN"


class Command_type(Enum):
    ENABLE_DEBUG = bitarray('11000000')
    DISABLE_DEBUG = bitarray('11000011')
    DELAY_INTERVAL = bitarray('11000101')
    REQUEST = bitarray('11001111')
    RESET = bitarray('00000000')
    START_SENDING = bitarray('11110011')
    STOP_SENDING = bitarray('11111100')
    ENABLE_SLEEP = bitarray('00001111')
    DISABLE_SLEEP = bitarray('00000011')
    ACK = 1 # no command, it's a Payload_type
    JOIN_ACK = 2 # no command, it's a Payload_type
    SET_INTERVAL = bitarray('11010101')
    SET_BLOCK = bitarray('00111100')
    REMOVE_BLOCK = bitarray('00110011')
    SET_DISTANCE = bitarray('10101110')
    REQUEST_ROUTE = bitarray('01001101')
    RESYNC_INTERVAL = bitarray('01101100')

    def from_str(name):
        if(name == "ENABLE_DEBUG"):
            return Command_type.ENABLE_DEBUG
        elif(name == "DISABLE_DEBUG"):
            return Command_type.DISABLE_DEBUG
        elif(name == "REQUEST"):
            return Command_type.REQUEST
        elif(name == "RESET"):
            return Command_type.RESET
        elif(name == "START_SENDING"):
            return Command_type.START_SENDING
        elif(name == "STOP_SENDING"):
            return Command_type.STOP_SENDING
        elif(name == "ENABLE_SLEEP"):
            return Command_type.ENABLE_SLEEP
        elif(name == "DISABLE_SLEEP"):
            return Command_type.DISABLE_SLEEP
        elif(name == "ACK"):
            return Command_type.ACK
        elif(name == "JOIN_ACK"):
            return Command_type.JOIN_ACK
        elif(name == "SET_INTERVAL"):
            return Command_type.SET_INTERVAL
        elif(name == "SET_BLOCK"):
            return Command_type.SET_BLOCK
        elif(name == "REMOVE_BLOCK"):
            return Command_type.REMOVE_BLOCK
        elif(name == "SET_DISTANCE"):
            return Command_type.SET_DISTANCE
        elif(name == "REQUEST_ROUTE"):
            return Command_type.REQUEST_ROUTE
        elif(name == "RESYNC_INTERVAL"):
            return Command_type.RESYNC_INTERVAL

        return None

    def __str__(self) -> str:
        if(self == Command_type.ENABLE_DEBUG):
            return "ENABLE_DEBUG"
        elif(self == Command_type.DISABLE_DEBUG):
            return "DISABLE_DEBUG"
        elif(self == Command_type.REQUEST):
            return "REQUEST"
        elif(self == Command_type.RESET):
            return "RESET"
        elif(self == Command_type.START_SENDING):
            return "START_SENDING"
        elif(self == Command_type.STOP_SENDING):
            return "STOP_SENDING"
        elif(self == Command_type.ENABLE_SLEEP):
            return "ENABLE_SLEEP"
        elif(self == Command_type.DISABLE_SLEEP):
            return "DISABLE_SLEEP"
        elif(self == Command_type.ACK):
            return "ACK"
        elif(self == Command_type.JOIN_ACK):
            return "JOIN_ACK"
        elif(self == Command_type.SET_INTERVAL):
            return "SET_INTERVAL"
        elif(self == Command_type.SET_BLOCK):
            return "SET_BLOCK"
        elif(self == Command_type.REMOVE_BLOCK):
            return "REMOVE_BLOCK"
        elif(self == Command_type.SET_DISTANCE):
            return "SET_DISTANCE"
        elif(self == Command_type.REQUEST_ROUTE):
            return "REQUEST_ROUTE"
        elif(self == Command_type.RESYNC_INTERVAL):
            return "RESYNC_INTERVAL"

        return "UNKNOWN"

class packet(object):
    def __init__(self, appID : bytes, sender : int, target : int, max_hops : int, packet_id : int, distance : int, direction : bool, payload_type : Payload_type, payload : bytes, target_dist : int = None, num_hops : int = 1, snr=None, rssi=None, origin=None):

        self.appID : bytes = appID
        # who sent the packet
        self.sender : int = sender
        # who created the packet in the first place
        if(origin is None):
            self.origin : int = sender
        else:
            self.origin : int = origin
        # who shall receive the packet
        self.target : int = target

        # flooding parameters
        self.max_hops : int = max_hops
        self.num_hops : int = num_hops
        self.packet_id : int = packet_id
        
        # distance vector based routing parameters
        # distance of the last sender
        self.last_distance : int = distance
        # direction of the packet UP=TRUE / DOWN=FALSE
        self.direction : bool = direction

        # receive params
        self.snr = snr
        self.rssi = rssi

        # distance of the target node
        if(target_dist is None):
            if( self.direction):
                self.target_distance : int = 0
            else:
                self.target_distance : int = 127
        else:
            self.target_distance : int = target_dist

        # type of payload
        self.payload_type : Payload_type = payload_type
        self.payload : bytes = payload

    def __copy__(self):
        cop = packet(self.appID, self.origin, self.target, self.max_hops, self.packet_id, self.last_distance, self.direction, self.payload_type, self.payload, num_hops=self.num_hops, snr=self.snr, rssi=self.rssi)
        cop.origin = self.origin

        return cop
    
    def to_bytes(self) -> bytearray:

        byte_array_list = self.appID
        byte_array_list += int(self.sender).to_bytes(1, byteorder='little')
        byte_array_list += int(self.origin).to_bytes(1, byteorder='little')
        byte_array_list += int(self.target).to_bytes(1, byteorder='little')
        byte_array_list += int(self.max_hops*16 + self.num_hops).to_bytes(1, byteorder='little')
        byte_array_list += int(self.packet_id).to_bytes(1, byteorder='little')    

        byte_array_list += int(self.direction*128 + self.last_distance).to_bytes(1, byteorder='little')
        byte_array_list += self.payload_type.value.tobytes()

        if(not self.payload is None):
            byte_array_list += self.payload       

        return byte_array_list

    # return the length of the packet payload in bytes
    def get_length(self):
        if(not self.payload is None):
            return 9 + len(self.payload)
        else:
            return 9

    def __str__(self) -> str:
        return "%s from %i sent by %i     payload: [%s]    hops: %s debug_name %s" % (str(self.payload_type)[13:], self.origin, self.sender, str(self.payload), str(self.hops), self.debug_name)
