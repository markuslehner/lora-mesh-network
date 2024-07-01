from sim.debugger import debugger
from hw.transceiver import transceiver
from hw.battery import battery

class node(object):

    def __init__(self, id : int, name : str , logic, batt : battery = None, x : int = 0, y : int = 0):
        self.id : int = id
        self.name : str = name
        self.logic = logic
        self.transceiver = transceiver(self)
        self.battery : battery = batt

        if(self.battery is None):
            self.mains_power = True
        else:
            self.mains_power = False

        # if chip is powered
        self.powered : bool = True
        # whether to perform reset of logic due to power outage
        self.reset : bool = False

        self.x : int = x
        self.y : int = y

        self.time : int = 0
        self.sleeping : bool = False
        self.sleep_timer : int = 0
        
        self.waiting : bool = False
        self.wait_timer : int = 0
        self.debugger : debugger = None

        self.logic.register(self)

        # debugging
        self.last_power_log = 0
        self.power_log_interval = 1000*60*10

    def set_debugger(self, debugger):
        self.debugger = debugger
        self.logic.set_debugger(debugger)
        self.transceiver.set_debugger(debugger)

    def register_in_world(self, world):
        self.transceiver.register_in_world(world)
        # self.solarpanel.register_in_world(world)

    def get_name(self) -> str:
        return self.name

    def position(self, x, y):
        self.x = x
        self.y = y

    def get_position(self):
        return self.x, self.y

    def get_transceiver(self) -> transceiver:
        return self.transceiver

    def set_time(self, time):
        self.time = time

    def get_time(self) -> int:
        return self.time

    def get_power_consumption(self):
        if(self.powered):
            if(self.sleeping):
                return self.transceiver.get_power_consumption() + 1000
            else:
                return self.transceiver.get_power_consumption() + 10000
        else:
            return 0

    def receive(self, packet) -> None:
        return None

    def sleep(self, time):
        self.sleeping = True
        self.sleep_timer = time
        self.waiting = False
        self.wait_timer = 0

    def wait(self, time):
        self.waiting = True
        self.wait_timer = time

    # update the hardware of the node
    # if CPU (logic) is sleeping don't call update
    # time is continuously updated, this is not teh case in the real hardware,
    # done here for ease of simulation
    # in real hardware the time the node is sleeping is added onto the current system time
    def update(self) -> None:

        # log battery
        if(self.get_time() - self.last_power_log > self.power_log_interval):
            self.last_power_log = self.get_time()

            if(self.mains_power):
                self.debugger.log("Node %s has mains power" % self.name, 4)
            elif(not self.battery is None):
                self.debugger.log("Node %s has %.2f %s battery remaining" % (self.name, self.battery.get_level() * 100, "%"), 4)
            else:
                self.debugger.log("Node %s is not powered", 4)

        # hardware power management
        if(self.mains_power):
            self.powered = True
        elif(not self.battery is None):
            if(self.battery.get_charge() > self.get_power_consumption()):
                self.powered = True
                # update battery level
                self.battery.update_charge(-self.get_power_consumption())
            else:
                # set reset flag to reset logic once power is restored
                if(self.powered):
                    self.reset = True
                    self.debugger.log("Node %s lost power" % self.name, 2)

                # update battery level
                self.battery.update_charge(-self.get_power_consumption())
                self.powered = False
        else:
            # set reset flag to reset logic once power is restored
            if(self.powered):
                self.reset = True
                self.debugger.log("Node %s lost power" % self.name, 2)

            self.powered = False

        # if has power, update loop
        if( self.powered ):
            # perform reset
            if(self.reset):
                self.debugger.log("Resetting node %s" % self.name, 2)
                self.logic.reset()
                self.reset = False
            # UPDATE FOR CPU (LOGIC)
            else:
                self.transceiver.update()
                self.time += 1

                if(self.sleeping):
                    if ( self.sleep_timer == 1):
                        self.sleep_timer = 0
                        self.sleeping = False
                    else:
                        self.sleep_timer -= 1
                elif(self.waiting):
                    if ( self.wait_timer == 1):
                        self.wait_timer = 0
                        self.waiting = False
                    else:
                        self.wait_timer -= 1        
                else:
                    self.logic.update_loop()
    
    def to_dict(self):
        if(self.battery is None):
            return {
                "type"      : type(self),
                "name"      : self.name,
                "id"        : self.id,
                "logic"     : self.logic.to_dict(),
                "battery"   : None,
                "x"         : self.x,
                "y"         : self.y
            }
        else:
            return {
                "type"      : type(self),
                "name"      : self.name,
                "id"        : self.id,
                "logic"     : self.logic.to_dict(),
                "battery"   : self.battery.to_dict(),
                "x"         : self.x,
                "y"         : self.y
            }
    @classmethod
    def from_dict(cls, d):
        if(d.get("battery") is None):
            instance = cls(
                d.get("id"),
                d.get("name"),
                d.get("logic").get("type").from_dict(d.get("logic")),
                None,
                x=d.get("x"),
                y=d.get("y")
            )
        else:
            instance = cls(
                d.get("id"),
                d.get("name"),
                d.get("logic").get("type").from_dict(d.get("logic")),
                d.get("battery").get("type").from_dict(d.get("battery")),
                x=d.get("x"),
                y=d.get("y")
            )
        return instance

    def __str__(self) -> str:
        return "%s with ID:%s @ x=%s y=%s using logic: %s" % (str(self.name).ljust(12), str(self.id).rjust(3), str(self.x).rjust(6), str(self.y).rjust(6), str(self.logic))


    