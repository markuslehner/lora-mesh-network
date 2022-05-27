from tracemalloc import stop
import numpy as np
import matplotlib.pyplot as plt
import tikzplotlib
from datetime import datetime
from lib import database
from pathlib import Path

# last time until which packets are counted
stop_time = datetime.strptime("2022-04-1 07:54:00", "%Y-%m-%d %H:%M:%S")


file_name = "data_db_04_01"
nodes = [1, 2, 3, 4]


database_file = str(Path(__file__).parent.parent) + "/hardware/RaspberryPi/db_saves/%s.db" % file_name
db = database.create_connection(database_file)

battery_logs = []
battery_times = []

for n in nodes:
    db_query = "SELECT battery, time_received FROM packets WHERE sender = 'Sensor_%s'" % str(n).zfill(2)
    print(db_query)
    cursor = db.execute(db_query)
    items = cursor.fetchall()

    if(len(items) == 0):
        raise Exception("Sensor_%s not in databse!" % str(n).zfill(2))

    battery_logs.append([it[0] for it in items if datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S") < stop_time])
    battery_times.append([ datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S") for it in items if datetime.strptime(it[1], "%Y-%m-%d %H:%M:%S") < stop_time])

# find first entry
oldest : datetime = battery_times[0][0]
youngest : datetime = battery_times[0][-1]

for i in range(1, len(nodes)):
    if(oldest > battery_times[i][0]):
        oldest = battery_times[i][0]

    if(youngest < battery_times[i][-1]):
        youngest = battery_times[i][-1]

battery_times_min = []

for i in range(len(nodes)):
    battery_times_min.append( [ 24*60*(dt - oldest).days + (dt - oldest).seconds/60 for dt in battery_times[i] if dt < stop_time ] )

# filter obviously wrong entries

for i in range(len(nodes)):

    for k in range(1, len(battery_times_min[i]) - 2):
        # difference is too high
        # without too big time difference
        diff_1 = abs(battery_logs[i][k-2] - battery_logs[i][k])
        diff_2 = abs(battery_logs[i][k] - battery_logs[i][k+2])
        time_diff = abs(battery_times_min[i][k-2] - battery_times_min[i][k+2])
        if(diff_1 > 5 and diff_2 > 5 and time_diff < 30):
            battery_logs[i][k] = (battery_logs[i][k-2] + battery_logs[i][k+2]) / 2
            pass

    for k in range(1, len(battery_times_min[i]) - 1):
        # difference is too high
        # without too big time difference
        diff_1 = abs(battery_logs[i][k-1] - battery_logs[i][k])
        diff_2 = abs(battery_logs[i][k] - battery_logs[i][k+1])
        time_diff = abs(battery_times_min[i][k-1] - battery_times_min[i][k+1])
        if(diff_1 > 5 and diff_2 > 5 and time_diff < 30):
            battery_logs[i][k] = (battery_logs[i][k-1] + battery_logs[i][k+1]) / 2
            pass

f, ax = plt.subplots(1, 1)
labels = []
for i in range(len(nodes)):

    ax.plot(battery_times_min[i], battery_logs[i])
    labels.append("node %i" % nodes[i])

ax.set_ylabel(r"$C_\mathrm{bat}(t)$")
ax.set_xlabel(r"$t$ in min")
ax.set_xlim((0, int(24*60*(youngest - oldest).days + (youngest - oldest).seconds/60)))
ax.grid()
ax.legend(labels)

tikzplotlib.save(str(Path(__file__).parent) + "/figures/battery_%s.tex" %  file_name, encoding="utf-8")

plt.show()