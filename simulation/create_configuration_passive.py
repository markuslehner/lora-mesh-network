from logic.handler_flooding_basic import handler_flooding_basic
from logic.handler_flooding import handler_flooding
from logic.logic_central_passive import logic_central_passive
from logic.logic_node_passive import logic_node_passive
from sim.event import event, event_action, event_command, event_dummy, event_reset, event_power

from hw.node_sensor import node_sensor
from hw.node import node
from hw.sensor import sensor
from hw.sensor import Sensor_Type
from hw.battery import battery

import sim.configuration_manager as cmanager

config_name = "world_passive"
appID = 123
SF = 7

# world setup
# if None, LoRa range chart is used
tx_min = 1500
tx_max = 2200
tx_error_rate = 0.05
tx_decay = 2

handler_to_use = handler_flooding_basic
interval = 1000*60*5

# set this to True when the offset for each node should be the same for each simulation
cmanager.use_same_offset = False

# create nodes
cmanager.register_node(node(
    100,
    "central",
    logic_central_passive(appID=appID, node_id=100, handler=handler_to_use(), spreading_f=SF),
    x=0,
    y=0
))

cmanager.register_node(node_sensor(
    1,
    "node1",
    logic_node_passive(appID, 1, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=200,
    y=0,
))

cmanager.register_node(node_sensor(
    2,
    "node2",
    logic_node_passive(appID, 2, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=800,
    y=0,
))

cmanager.register_node(node_sensor(
    3,
    "node3",
    logic_node_passive(appID, 3, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1400,
    y=0,
))

cmanager.register_node(node_sensor(
    4,
    "node4",
    logic_node_passive(appID, 4, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1600,
    y=0,
))

cmanager.register_node(node_sensor(
    5,
    "node5",
    logic_node_passive(appID, 5, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1800,
    y=0,
))

cmanager.register_node(node_sensor(
    6,
    "node6",
    logic_node_passive(appID, 6, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=2000,
    y=0,
))

cmanager.register_node(node_sensor(
    7,
    "node7",
    logic_node_passive(appID, 7, interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=2200,
    y=0,
))

# cmanager.register_event(event_dummy(cmanager.world_time + 10000))
# cmanager.register_event(event_reset(cmanager.world_time + 1000*60*60*1.2, 5))
# cmanager.register_event(event_power(world_time + 1000*60*60*2 + 1000*60*10, 5, False))
# cmanager.register_event(event_power(world_time + 1000*60*60*4 + 1000*60*10, 5, True))

cmanager.set_tx_params(tx_min, tx_max, tx_error_rate, tx_decay)
cmanager.write_configuration(config_name)