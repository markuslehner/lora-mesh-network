from matplotlib import cm
from hw.packet import Command_type
from logic.command.command import nack_command
from logic.logic_node_lmn import logic_node_lmn
from logic.handler_lmn import handler_lmn
from logic.handler_flooding_basic import handler_flooding_basic
from logic.logic_central_lmn import logic_central_lmn
from sim.event import event, event_action, event_command, event_dummy, event_reset, event_power

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


logic_to_use = logic_node_lmn
handler_to_use = handler_lmn

# create nodes
cmanager.register_node(node(
    100,
    "central",
    logic_central_lmn(appID=appID, node_id=100, interval=1000*60*10, handler=handler_to_use(), spreading_f=SF),
    x=400,
    y=400
))

cmanager.register_node(node_sensor(
    1,
    "node1",
    logic_to_use(appID, 1, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=800,
    y=800,
))

cmanager.register_node(node_sensor(
    2,
    "node2",
    logic_to_use(appID, 2, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=800,
    y=400,
))

cmanager.register_node(node_sensor(
    3,
    "node3",
    logic_to_use(appID, 3, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=800,
    y=0,
))

cmanager.register_node(node_sensor(
    4,
    "node4",
    logic_to_use(appID, 4, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=400,
    y=0,
))

cmanager.register_node(node_sensor(
    5,
    "node5",
    logic_to_use(appID, 5, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=0,
    y=0,
))

cmanager.register_node(node_sensor(
    6,
    "node6",
    logic_to_use(appID, 6, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=0,
    y=400,
))

cmanager.register_node(node_sensor(
    7,
    "node7",
    logic_to_use(appID, 7, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=0,
    y=800,
))

cmanager.register_node(node_sensor(
    8,
    "node8",
    logic_to_use(appID, 8, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=400,
    y=800,
))

cmanager.register_node(node_sensor(
    9,
    "node9",
    logic_to_use(appID, 9, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=1200,
    y=800,
))

cmanager.register_node(node_sensor(
    10,
    "node10",
    logic_to_use(appID, 10, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=1200,
    y=400,
))

cmanager.register_node(node_sensor(
    11,
    "node11",
    logic_to_use(appID, 11, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=None,
    x=1200,
    y=0,
))

cmanager.register_block(9,7)
cmanager.register_block(10,7)
cmanager.register_block(11,7)
cmanager.register_block(9,6)
cmanager.register_block(10,6)
cmanager.register_block(11,6)
cmanager.register_block(9,5)
cmanager.register_block(10,5)
cmanager.register_block(11,5)

cmanager.register_block(9,8)
cmanager.register_block(10,8)
cmanager.register_block(11,8)
cmanager.register_block(9,100)
cmanager.register_block(10,100)
cmanager.register_block(11,100)
cmanager.register_block(9,4)
cmanager.register_block(10,4)
cmanager.register_block(11,4)

cmanager.register_block(1,7)
cmanager.register_block(2,7)
cmanager.register_block(3,7)
cmanager.register_block(1,6)
cmanager.register_block(2,6)
cmanager.register_block(3,6)
cmanager.register_block(1,5)
cmanager.register_block(2,5)
cmanager.register_block(3,5)

cmanager.register_block(5,7)
cmanager.register_block(4,7)
cmanager.register_block(3,7)
cmanager.register_block(11,7)
cmanager.register_block(5,8)
cmanager.register_block(4,8)
cmanager.register_block(3,8)
cmanager.register_block(11,8)
cmanager.register_block(5,1)
cmanager.register_block(4,1)
cmanager.register_block(3,1)
cmanager.register_block(11,1)
cmanager.register_block(5,9)
cmanager.register_block(4,9)
cmanager.register_block(3,9)
cmanager.register_block(11,9)

# cmanager.register_event(event_dummy(cmanager.world_time + 10000))
# cmanager.register_event(event_reset(cmanager.world_time + 1000*60*60*1.2, 5))
cmanager.register_event(event_command(cmanager.world_time + 1000*60*60*2.2, nack_command(0, Command_type.ENABLE_SLEEP, prio=2)))
cmanager.register_event(event_command(cmanager.world_time + 1000*60*60*2.2 + 20, nack_command(0, Command_type.ENABLE_SLEEP, prio=2)))
# cmanager.register_event(event_command(cmanager.world_time + 1000*60*60*2.3, nack_command(0, Command_type.ENABLE_SLEEP, prio=2)))
# cmanager.register_event(event_command(cmanager.world_time + 1000*60*60*2 + 1000*60*10, nack_command(0, Command_type.ENABLE_SLEEP, prio=2)))
# cmanager.register_event(event_power(world_time + 1000*60*60*2 + 1000*60*10, 5, False))
# cmanager.register_event(event_power(world_time + 1000*60*60*4 + 1000*60*10, 5, True))

cmanager.set_tx_params(tx_min, tx_max, tx_error_rate, tx_decay)
cmanager.write_configuration(config_name)