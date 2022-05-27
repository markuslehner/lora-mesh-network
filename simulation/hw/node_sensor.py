from hw.node import node
from hw.sensor import sensor
from hw.battery import battery

class node_sensor(node):

    def __init__(self , id : int, name : str, logic, sens : sensor, batt : battery=None, x:int=0, y:int=0) -> None:
        super().__init__(id, name, logic, batt=batt, x=x, y=y)
        self.sensor : sensor = sens

    def get_power_consumption(self):
        return super().get_power_consumption() + self.sensor.get_power_consumption()

    def to_dict(self):
        d = super().to_dict()
        d.update({"sensor" : self.sensor.to_dict()
            })
        return d

    @classmethod
    def from_dict(cls, d):

        if(d.get("battery") is None):
            instance = cls(
                d.get("id"),
                d.get("name"),
                d.get("logic").get("type").from_dict(d.get("logic")),
                sensor.from_dict(d.get("sensor")),
                None,
                x=d.get("x"),
                y=d.get("y")
            )
        else:
            instance = cls(
                d.get("id"),
                d.get("name"),
                d.get("logic").get("type").from_dict(d.get("logic")),
                sensor.from_dict(d.get("sensor")),
                d.get("battery").get("type").from_dict(d.get("battery")),
                x=d.get("x"),
                y=d.get("y")
            )
        return instance