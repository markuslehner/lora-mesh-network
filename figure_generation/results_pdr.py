import numpy as np
import math
from datetime import datetime

from lib import database
from pathlib import Path

file_name = "data_db_04_02"
nodes = [1, 2, 3, 4, 5, 6]

interval = 5 # min

start_time = datetime.strptime("2022-03-31 07:09:00", "%Y-%m-%d %H:%M:%S")
stop_time = datetime.strptime("2022-04-01 16:34:00", "%Y-%m-%d %H:%M:%S")


database_file = str(Path(__file__).parent.parent) + "/hardware/RaspberryPi/db_saves/%s.db" % file_name
db = database.create_connection(database_file)

battery_logs = []
removed_doubles = np.zeros((len(nodes)))

for n in range(len(nodes)):
    cursor = db.execute("SELECT battery, time_received FROM packets WHERE sender = 'Sensor_%s'" % str(nodes[n]).zfill(2))
    items = cursor.fetchall()

    if(len(items) == 0):
        raise Exception("Sensor_%s not in databse!" % str(nodes[n]).zfill(2))

    packets_from_sensor = []
    last_time : datetime = None

    for it in items:
        current_time = datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S")
        if ( current_time < stop_time and current_time > start_time ):
            if(last_time is None or (current_time - last_time).seconds > 30):
                packets_from_sensor.append(it[0])
            else:
                removed_doubles[n] += 1

        last_time = current_time

    battery_logs.append(packets_from_sensor)

    # battery_logs.append([it[0] for it in items if datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S") < stop_time and datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S") > start_time])


# num target
interval_length = 24*60*(stop_time - start_time).days + (stop_time - start_time).seconds/60
target_packets = math.floor(interval_length / interval)

print("Intervallength of %.2f min --> %i packets" % (interval_length, target_packets))

overall_rx = 0
overall_tx = target_packets*len(nodes)

for i in range(len(nodes)):
    print("Node %i: %i/%i --> %.2f%%, removed %i doubles" % (nodes[i], len(battery_logs[i]), target_packets, 100*len(battery_logs[i])/target_packets, int(removed_doubles[i]) ) )
    overall_rx += len(battery_logs[i])

print("")
print("Overall PDR: %i/%i --> %.2f%%" % (overall_rx, overall_tx, 100*overall_rx/overall_tx) )