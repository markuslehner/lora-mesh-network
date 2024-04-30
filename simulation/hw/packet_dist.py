from hw.packet_flooding import packet_flooding

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

        cop.second_last_node = self.second_last_node
        cop.num_hops = self.num_hops

        return cop
