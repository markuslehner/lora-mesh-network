
class solarpanel(object):

    def __init__(self) -> None:
        super().__init__()
        self.maxAmp = 100

    def register_in_world(self, world):
        self.world = world

    def get_current_amp(self):
        return self.world.get_weather() * self.maxAmp
