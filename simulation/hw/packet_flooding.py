from hw.packet import lora_packet, Payload_type, Command_type

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
