from hw.packet import packet

class packet_handler(object):

    def __init__(self):
        super().__init__()

    def register(self, node):
        self.node = node

    """
    Handles a received packet
    """
    def handle_packet(self, packet : packet) -> None:
        return None

    """
    decide if packet needs to be re-transmittied
    prepare packet for furhter transport
    """
    def relay_packet(self, packet : packet) -> None:
        return None

    @classmethod
    def from_dict(cls, d):
        return cls()
