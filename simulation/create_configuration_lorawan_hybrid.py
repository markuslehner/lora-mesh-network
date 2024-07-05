from logic.logic_node_lorawan_hybrid import logic_node_lorawan_hybrid
from logic.logic import logic_gateway_lorawan
from logic.server_lorawan_hybrid import server_lorawan_hybrid

from hw.node_sensor import node_sensor
from hw.node import node
from hw.sensor import sensor
from hw.sensor import Sensor_Type
from hw.battery import battery

import sim.configuration_manager as cmanager

config_name = "world_lorawan_hybrid"
appID = 123
NwkKey = 345
SF = 7

# world setup
# if None, LoRa range chart is used
tx_min = 1500
tx_max = 2200
tx_error_rate = 0.015
tx_decay = 2

interval = 1000*60*5
logic_to_use = logic_node_lorawan_hybrid

cmanager.register_server(
    server_lorawan_hybrid(appID, NwkKey)
)

# create nodes
cmanager.register_node(node(
    100,
    "GW1",
    logic_gateway_lorawan(appID, 100, None, spreading_f=SF),
    x=0,
    y=0
))

cmanager.register_node(node_sensor(
    1,
    "node1",
    logic_to_use(appID, 1, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=800,
    y=0,
))

cmanager.register_node(node_sensor(
    2,
    "node2",
    logic_to_use(appID, 2, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1200,
    y=0,
))

cmanager.register_node(node_sensor(
    3,
    "node3",
    logic_to_use(appID, 3, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=800,
    y=400,
))

cmanager.register_node(node_sensor(
    4,
    "node4",
    logic_to_use(appID, 4, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=800,
    y=-400,
))

cmanager.register_node(node_sensor(
    5,
    "node5",
    logic_to_use(appID, 5, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=-800,
    y=0,
))

cmanager.register_node(node_sensor(
    6,
    "node6",
    logic_to_use(appID, 6, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=-1200,
    y=0,
))

cmanager.register_node(node_sensor(
    7,
    "node7",
    logic_to_use(appID, 7, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=-800,
    y=400,
))

cmanager.register_node(node_sensor(
    8,
    "node8",
    logic_to_use(appID, 8, interval, NwkKey, spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=-800,
    y=-400,
))

cmanager.register_block(100, 2)
cmanager.register_block(100, 3)
cmanager.register_block(100, 4)

cmanager.register_block(100, 6)
cmanager.register_block(100, 7)
cmanager.register_block(100, 8)

cmanager.set_tx_params(tx_min, tx_max, tx_error_rate, tx_decay)
cmanager.write_configuration(config_name)