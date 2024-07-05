from logic.logic_node_join_dist_pid import logic_node_dist_pid
from logic.handler_dist_pid import handler_dist_pid
from logic.logic import logic_gateway_lora
from logic.server_join import server_join

from hw.node_sensor import node_sensor
from hw.node import node
from hw.sensor import sensor, Sensor_Type
from hw.battery import battery

import sim.configuration_manager as cmanager

config_name = "world_join_server"
appID = 123
send_interval = 1000*60*5

# Transmission model
# if None, LoRa range chart is used
SF = 7
tx_min = 1500
tx_max = 2200
tx_error_rate = 0.05
tx_decay = 2


logic_to_use = logic_node_dist_pid
handler_to_use = handler_dist_pid


cmanager.register_server(
    server_join(appID)
)

# create nodes
cmanager.register_node(node(
    100,
    "central",
    logic_gateway_lora(appID=appID, node_id=100, handler=handler_to_use(), spreading_f=SF),
    x=0,
    y=0
))

cmanager.register_node(node_sensor(
    1,
    "node1",
    logic_to_use(appID, 1, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=200,
    y=0,
))

cmanager.register_node(node_sensor(
    2,
    "node2",
    logic_to_use(appID, 2, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=800,
    y=0,
))

cmanager.register_node(node_sensor(
    3,
    "node3",
    logic_to_use(appID, 3, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1400,
    y=0,
))

cmanager.register_node(node_sensor(
    4,
    "node4",
    logic_to_use(appID, 4, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1600,
    y=0,
))

cmanager.register_node(node_sensor(
    5,
    "node5",
    logic_to_use(appID, 5, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=1800,
    y=0,
))

cmanager.register_node(node_sensor(
    6,
    "node6",
    logic_to_use(appID, 6, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=2000,
    y=0,
))

cmanager.register_node(node_sensor(
    7,
    "node7",
    logic_to_use(appID, 7, send_interval, handler=handler_to_use(), spreading_f=SF),
    sensor(Sensor_Type.TEMP),
    batt=battery(1200,1.0),
    x=2200,
    y=0,
))

cmanager.set_tx_params(tx_min, tx_max, tx_error_rate, tx_decay)
cmanager.set_runtime(1000*60*60*1 + 1000*60*8)
cmanager.write_configuration(config_name)