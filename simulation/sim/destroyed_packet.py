from enum import Enum
import datetime

class Destruction_type(Enum):
    WORLD = 1
    FORWARD = 2
    COLLISION = 3
    SLEEP = 4

class Forward_type(Enum):

    RETURN_TO_SENDER = 1
    FLOOD_LIMIT = 2
    RETURN_TO_LAST = 3
    BOUNCE = 4
    RELAY_BLOCK = 5
    DISTANCE = 6
    CONNECTED = 7

    def __str__(self) -> str:

        if(self == Forward_type.RETURN_TO_SENDER):
            return "return to sender"
        elif(self == Forward_type.FLOOD_LIMIT):
            return "flood limit"
        elif(self == Forward_type.RETURN_TO_LAST):
            return "return to last node"
        elif(self == Forward_type.BOUNCE):
            return "bounce"
        elif(self == Forward_type.RELAY_BLOCK):
            return "relay_block_time"
        elif(self == Forward_type.DISTANCE):
            return "distance"
        elif(self == Forward_type.CONNECTED):
            return "not connected"

        return ""
        

class destroyed_packet(object):

    def __init__(self, packet, sender, receiver, reason, fwd_reason=None, collision_packets=[], largest_relay=0, relay_block=0, time=None) -> None:
        super().__init__()

        # the packet 
        self.packet = packet

        # the last sender, not the origin
        self.sender : int = sender

        # the last recipient, not the target
        self.receiver : int = receiver

        # the reason why the packet was destroyed
        self.reason : Destruction_type = reason

        # the reason the packet was not forwarded
        self.fwd_reason : Forward_type = fwd_reason

        # list of other packets destroyed in collision
        self.collision_packets = []
        for p in collision_packets:
            if(not p is None):
                self.collision_packets.append(p.debug_name)

        # largest entry in relay block, that stopped relaying
        self.largest_relay = largest_relay

        # time until the next packet from same origin is forwarded
        self.relay_block = relay_block

        #the time the packet was destroyed
        self.time = time

    def __str__(self) -> str:

        timestamp = datetime.datetime.fromtimestamp(self.time/1000).strftime("%H:%M:%S.%f")[:-3]

        if(self.reason == Destruction_type.WORLD):
            return "[%s] destroyed in world: %i -> %i   %s" % (timestamp, self.sender, self.receiver, str(self.packet.hops))
        elif(self.reason == Destruction_type.FORWARD):
            if(self.fwd_reason == Forward_type.RELAY_BLOCK):
                str_fwd = "%s (%i/%i)" % (str(self.fwd_reason), self.largest_relay, self.relay_block)
            else:
                str_fwd = str(self.fwd_reason)

            return "[%s] not forwarded at node %s (from: %i), because: %s   %s" % (timestamp, self.receiver, self.sender, str_fwd, str(self.packet.hops))
        elif(self.reason == Destruction_type.COLLISION):
            return "[%s] Collision at node %i (from %i)   %s  other packets: %s" % (timestamp, self.receiver, self.sender, str(self.packet.hops), str(self.collision_packets))
        elif(self.reason == Destruction_type.SLEEP):
            return "[%s] Reached node %i (from %i) while it was sleeping" % (timestamp, self.receiver, self.sender)

        return "destroyed_packet placeholder"


    

