from bitarray import bitarray
from enum import Enum
from sim.utils import get_air_time
from typing import List

class Packet_type(Enum):
    LORAWAN = 1
    LORA = 2


class LoRaWAN_type(Enum):
    JOIN_REQUEST = 1
    JOIN_ACCEPT = 2
    UNCONFIRMED_DATA_UP = 3
    UNCONFIRMED_DATA_DOWN = 4
    CONFIRMED_DATA_UP = 5
    CONFIRMED_DATA_DOWN = 6
    RFU = 7


class Payload_type(Enum):

    # main types
    JOIN = bitarray('11110000')
    JOIN_ACK = bitarray('00001111')
    TIME_SYNC = bitarray('11001100')
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
        elif(int(pl_type).to_bytes(1, byteorder='little') == Payload_type.TIME_SYNC.value.tobytes()):
            return Payload_type.TIME_SYNC
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
        elif(self == Payload_type.TIME_SYNC):
            return "TIME_SYNC"
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
    def __init__(self, pkt_t : Packet_type) -> None:
        self.packet_type : Packet_type = pkt_t
        self.frequency : float = 0
        self.modulation : str = None
        self.bandwidth : float = 0
        self.tx_power : int = 0
        self.rssi : int = 0
        self.time_received : int = 0

    # set sending parameters
    def send(self, freq, mod, band, tx_power):
        self.frequency = freq
        self.modulation = mod
        self.bandwidth = band
        self.tx_power = tx_power

    def set_rssi(self, rssi):
        self.rssi = rssi

    def set_receive_time(self, time):
        self.time_received = time

    def get_length(self) -> int:
        return 20

    def get_air_time(self) -> int:
        return get_air_time(self.frequency, self.modulation, self.bandwidth, self.get_length())


class lora_packet(packet):
    def __init__(self, appID, sender, target, payload_type, payload, debug_name=None):
        super().__init__(Packet_type.LORA)
        self.appID : int = appID
        # who sent the packet
        self.sender : int = sender
        # who created the packet in the first place
        self.origin : int = sender
        # who shall receive the packet
        self.target : int = target
        # type of payload
        self.payload_type = payload_type
        self.payload = payload

        # RSSI when the packet was last received
        self.rssi : int = 0

        # sending parameters
        self.frequency : float = None
        self.modulation : str = None
        self.bandwidth : float = None
        self.tx_power : float = None

        # debug
        self.time_received : int = 0
        self.debug_name = debug_name
        self.hops : List[int] = []
        self.hops.append(sender)
        #if packet was corrupted during reception
        self.corrupted : bool = False

    def __copy__(self):
        cop = lora_packet(self.appID, self.origin, self.target, self.payload_type, self.payload, debug_name=self.debug_name)
        cop.origin = self.origin
        cop.frequency = self.frequency
        cop.bandwidth = self.bandwidth
        cop.modulation = self.modulation
        cop.tx_power = self.tx_power
        
        cop.hops = self.hops.copy()
        return cop
    
    # return the length of the packet payload in bytes
    def get_length(self):
        if(self.payload_type == Payload_type.ACK):
            return 9
        elif(self.payload_type == Payload_type.JOIN):
            return 11
        elif(self.payload_type == Payload_type.DATA):
            return 26
        elif(self.payload_type == Payload_type.COMMAND):
            if(self.payload[0] == Command_type.DELAY_INTERVAL):
                return 11
            elif(self.payload[0] == Command_type.SET_INTERVAL):
                return 26
            else:
                return 10
        else:
            return 15

    def add_hop(self, node):
        self.sender = node.id
        self.hops.append(node.id)

    def __str__(self) -> str:
        return "%s from %i sent by %i     payload: [%s]    hops: %s debug_name %s received at %s" % (str(self.payload_type), self.origin, self.sender, str(self.payload), str(self.hops), self.debug_name)
    

class packet_flooding(lora_packet):

    def __init__(self, appID, sender, target, payload_type, payload, max_hops, packet_id=None, debug_name=None):
        super().__init__(appID, sender, target, payload_type, payload, debug_name=debug_name)

        # flooding parameters
        self.max_hops = max_hops
        self.num_hops = 1
        self.packet_id = packet_id
    
    def __copy__(self):
        cop = packet_flooding(self.appID, self.sender, self.target, self.payload_type, self.payload, self.max_hops, packet_id=self.packet_id, debug_name=self.debug_name)
        cop.origin = self.origin
        cop.frequency = self.frequency
        cop.bandwidth = self.bandwidth
        cop.modulation = self.modulation       
        cop.hops = self.hops.copy()

        cop.num_hops = self.num_hops

        return cop

    def add_hop(self, node):
        super().add_hop(node)
        self.num_hops += 1

    def __str__(self) -> str:
        if(self.packet_id is None):
            return "%s from %i with %i hops payload: %s    hops: %s debug_name: %s" % (str(self.payload_type), self.origin, self.num_hops, str(self.payload), str(self.hops), self.debug_name)
        else:
            return "%s from %i with %i hops payload: %s    hops: %s debug_name: %s PID: %i" % (str(self.payload_type), self.origin, self.num_hops, str(self.payload), str(self.hops), self.debug_name, self.packet_id)


class packet_dist(packet_flooding):

    def __init__(self, appID, sender, target, max_hops, packet_id, distance, direction, payload_type, payload, target_dist=None, debug_name=None):
        super().__init__(appID, sender, target, payload_type, payload, max_hops, packet_id=packet_id, debug_name=debug_name)

        # distance vector based routing parameters
        # distance of the last sender
        self.last_distance = distance
        # direction of the packet UP=TRUE / DOWN=FALSE
        self.direction = direction

        # distance of the target node
        if(target_dist is None):
            if( self.direction):
                self.target_distance = 0
            else:
                self.target_distance = 127
        else:
            self.target_distance = target_dist

    def add_hop(self, node):
        self.last_distance = node.logic.distance
        return super().add_hop(node)

    def __copy__(self):
        cop = packet_dist(self.appID, self.sender, self.target, self.max_hops, self.packet_id, self.last_distance, self.direction, self.payload_type, self.payload, target_dist=self.target_distance, debug_name=self.debug_name)
        cop.origin = self.origin
        cop.frequency = self.frequency
        cop.bandwidth = self.bandwidth
        cop.modulation = self.modulation       
        cop.hops = self.hops.copy()
        cop.num_hops = self.num_hops

        return cop


class lorawan_packet(lora_packet):
    def __init__(self, appID : int , sender : int, target : int, payload_type : LoRaWAN_type, payload : List[int], packet_id : int, debug_name=None):
        super().__init__(appID, sender, target, payload_type, payload, debug_name=debug_name)
        self.packet_type : Packet_type = Packet_type.LORAWAN
        self.payload_type : LoRaWAN_type = payload_type
        self.packet_id : int = packet_id

    def __copy__(self):
        cop = lorawan_packet(self.appID, self.sender, self.target, self.payload_type, self.payload, self.packet_id, debug_name=self.debug_name)
        cop.frequency = self.frequency
        cop.bandwidth = self.bandwidth
        cop.modulation = self.modulation       

        return cop

    def get_length(self):
        return 26 # TODO
    
    def __str__(self) -> str:
        return "LORAWAN packet from %i with payload: %s debug_name: %s" % (self.sender, str(self.payload), self.debug_name)