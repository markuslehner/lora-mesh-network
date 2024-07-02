from simulation.logic.logic_node_lorawan import logic_node_lora
from simulation.logic.logic_central_lorawan import logic_central_lora

from hw.node_sensor import node_sensor
from hw.node import node
from hw.sensor import sensor
from hw.sensor import Sensor_Type
from hw.battery import battery

import sim.configuration_manager as cmanager

config_name = "world_paper"
appID = 123
SF = 7

# world setup
# if None, LoRa range chart is used
tx_min = 1500
tx_max = 2200
tx_error_rate = 0.05
tx_decay = 2


logic_to_use = logic_node_lora

# create nodes
cmanager.register_node(node(
    100,
    "central",
    logic_central_lora(appID=appID, spreading_f=SF),
    x=400,
    y=400
))

cmanager.register_node(node_sensor(
    1,
    "node1",
    logic_to_use(appID, 1, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=800,
    y=800,
))

cmanager.set_tx_params(tx_min, tx_max, tx_error_rate, tx_decay)
cmanager.write_configuration(config_name)