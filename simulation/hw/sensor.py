import numpy as np
from enum import Enum
import random

class Sensor_Type(Enum):
     TEMP = 1
     TEMP_HUM = 2
     RADIATION = 3

class sensor(object):

    def __init__(self, type):
        self.type = type
        # if sensor is powered
        self.active = True

    def get_power_consumption(self):
        return self.active * 1000

    def get_value(self):

        if(self.type == Sensor_Type.TEMP):
            return random.randint(7, 44)
        elif(self.type == Sensor_Type.TEMP_HUM):
            return 2.0
        elif(self.type == Sensor_Type.RADIATION):
            return 3.0 

    def to_dict(self):
        return {"type" : self.type}

    @classmethod
    def from_dict(cls, d):
        return cls(d.get("type"))

    