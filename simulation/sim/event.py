from logic.command.command import command
from logic.command.action import action

class event(object):
    def __init__(self, time) -> None:
        super().__init__()

        # time when the event is executed
        self.execution_time = time

    # execute the event in the provided world
    def execute(self, world):
        pass

class event_application(event):
    def __init__(self, time : int, app : int) -> None:
        super().__init__(time)

        self.application = app

    def execute(self, world, central_logic):
        pass


class event_command(event_application):
    def __init__(self, time, com) -> None:
        super().__init__(time)

        self.command = com

    def execute(self, world, central_logic):
        central_logic.command_center.register_command(self.command)


class event_action(event_application):
    def __init__(self, time, act : action) -> None:
        super().__init__(time)

        self.action = act

    def execute(self, world, central_logic):
        central_logic.action_center.register_action(self.action)       


class event_dummy(event):
    def __init__(self, time : int) -> None:
        super().__init__(time)

    def execute(self, world):
        world.debugger.log("DUMMY EVENT", 2) 


class event_reset(event):
    def __init__(self, time : int, id : int) -> None:
        super().__init__(time)
        self.node_id: int = id

    def execute(self, world):
        world.debugger.log("RESET EVENT: resetting node %i" % self.node_id, 2)
        for n in world.get_nodes():
            if n.id == self.node_id:
                n.reset = True
                break


class event_power(event):
    def __init__(self, time : int, id : int, power_state : bool) -> None:
        super().__init__(time)
        self.node_id: int = id
        self.power : bool = power_state

    def execute(self, world):
        world.debugger.log("POWER EVENT: setting power status of node %i to %s" % (self.node_id, str(self.power) ), 2)
        for n in world.get_nodes():
            if n.id == self.node_id:
                n.mains_power = self.power
                break