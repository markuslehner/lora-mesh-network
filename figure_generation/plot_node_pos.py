import matplotlib.pyplot as plt
import numpy as np
import tikzplotlib

from lib import map_plot
from pathlib import Path

nue = False
save_name = "node_pos"

long_min = 8.4046
long_max = 8.4171
lat_min = 49.0096
lat_max = 49.0154
# background_img = plt.imread(os.getcwd() + '/gps/map_ka.png')
# if set to noe it will be dynamicall loaded from openstreetmaps.org
background_img = None

positions = [
    (8.4094, 49.0128, "100", "r"),
    (8.4096, 49.0125, "1", "b"),
    (8.41215, 49.01142, "2", "b"),
    (8.41344, 49.01116, "3", "b"),
    (8.4150, 49.0108, "4", "b"),
    (8.4159, 49.01185, "5", "b"),
    (8.4148, 49.0098, "6", "b")
]

longitude = np.zeros((len(positions)))
latitude = np.zeros((len(positions)))
name = np.zeros((len(positions)))
color = []

error_cnt = 0
error_idx = []

for i in range(len(positions)):
    longitude[i] = positions[i][0]
    latitude[i] = positions[i][1]
    name[i] = positions[i][2]
    color.append(positions[i][3])


# PLOTTING
fig, ax = plt.subplots(num=1)

ax.set_xlim(long_min, long_max)
ax.set_ylim(lat_min, lat_max)

if(background_img is None):
    lat_deg = lat_min
    lon_deg = long_min
    delta_lat = lat_max-lat_min
    delta_long = long_max-long_min
    zoom = 17

    long_min_r, lat_max_r = map_plot.deg2num(lat_deg, lon_deg, zoom)
    long_max_r, lat_min_r = map_plot.deg2num(lat_deg + delta_lat, lon_deg + delta_long, zoom)

    bound_max_lat, bound_min_long = map_plot.num2deg(long_min_r, lat_min_r, zoom)
    bound_min_lat, bound_max_long = map_plot.num2deg(long_max_r, lat_max_r, zoom)

    lat_step = (bound_max_lat-bound_min_lat)/(lat_max_r-lat_min_r)
    long_step = (bound_max_long-bound_min_long)/(long_max_r-long_min_r)

    background_img = map_plot.getImageCluster(lat_deg, lon_deg, delta_lat,  delta_long, zoom)
    print("bounds: lat-min: %f lat-max: %f long-min: %f long-max: %f" % (bound_min_lat-lat_step, bound_max_lat, bound_min_long, bound_max_long+long_step))
    ax.imshow(background_img, zorder=0, extent = (bound_min_long, bound_max_long+long_step, bound_min_lat-lat_step, bound_max_lat), aspect= 'equal')
else:
    ax.imshow(background_img, zorder=0, extent = (long_min, long_max, lat_min, lat_max), aspect= 'equal')
    print("bounds: lat-min: %f lat-max: %f long-min: %f long-max: %f" % (lat_min, lat_max, long_min, long_max,))

dpi = 80
width, height = background_img.size

# What size does the figure need to be in inches to fit the image?
fig.set_figheight(height / float(dpi))
fig.set_figwidth(width / float(dpi))

sc = ax.scatter(longitude, latitude, zorder=1, alpha=0.5, c=color, s=200)
ax.set_xlabel("longitude")
ax.set_ylabel("latitude")

for i in range(len(positions)):
    ax.text(positions[i][0], positions[i][1], positions[i][2], rotation=0 , fontsize=8, ha='center', va='center')  

tikzplotlib.save(str(Path(__file__).parent) + "/figures/%s.tex" % save_name, encoding="utf-8")

ax.set_title('Plotting GPS data')
plt.show()