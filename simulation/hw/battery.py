class battery(object):

    # @param capacity in mAh
    # @param charge in fraction [0;1.0]
    def __init__(self, capacity, charge) -> None:
        super().__init__()
        
        # capactity of the battery in uA ms
        self.capacity : int = capacity*60*60*1000*1000
        # remaining charge of the battery in uA ms
        self.charge : int = self.capacity * charge
        # for saving to dict
        self.first_charge = charge

    # returns current charge level of battery
    def get_charge(self):
        return self.charge

    def get_capacity(self):
        return self.capacity

    def get_level(self) -> float:
        return self.charge / self.capacity

    # deduct or add 'net_charge' from/to the current charge level of the battery
    def update_charge(self, net_charge):
        self.charge += net_charge

        if(self.charge > self.capacity):
            self.charge = self.capacity
        elif(self.charge < 1):
            self.charge = 0

    def to_dict(self) -> dict:
        return {
            "type"      : type(self),
            "capacity"  : self.capacity,
            "charge"    : self.first_charge
        }

    @classmethod    
    def from_dict(cls, d):
        instance = cls(
            d.get("capacity") / (60*60*1000*1000),
            d.get("charge")
        )
        return instance