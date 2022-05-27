import matplotlib.pyplot as plt
import matplotlib.cm
import numpy as np
from pathlib import Path
import tikzplotlib

from lib import map_plot, database


database_file = str(Path(__file__).parent.parent) + "/hardware/RaspberryPi/db_saves/gps_db_7_1.db"

save_name = "range_testing_sf10_ka"
write_tex = False

long_min = 8.4046
long_max = 8.4171
lat_min = 49.0096
lat_max = 49.0154
# background_img = plt.imread(os.getcwd() + '/gps/map_ka.png')
# if set to none it will be dynamicall loaded from openstreetmaps.org
background_img = None

db = database.create_connection(database_file)

cursor = db.execute('SELECT longitude, latitude, rssi FROM packets')
items = cursor.fetchall()

longitude = np.zeros((len(items)))
latitude = np.zeros((len(items)))
rssi = np.zeros((len(items)))

error_cnt = 0
error_idx = []

for i in range(len(items)):
    longitude[i] = items[i][0]
    latitude[i] = items[i][1]
    rssi[i] = items[i][2]

    error = False
    if(rssi[i] < -120 or rssi[i] > -30):
        error = True
    elif(longitude[i] < long_min or longitude[i] > long_max):
        error = True
    elif(latitude[i] < lat_min or latitude[i] > lat_max):
        error = True
    elif(i < 0):
        error = True

    if(error):
        error_cnt += 1
        error_idx.append(i)


longitude_filtered = np.zeros((len(longitude)-error_cnt))
latitude_filtered = np.zeros((len(longitude)-error_cnt))
rssi_filtered = np.zeros((len(longitude)-error_cnt))

offset = 0
for i in range(len(items)):
    if(i in error_idx):
        offset += 1
    else:
        longitude_filtered[i-offset] = longitude[i]
        latitude_filtered[i-offset] = latitude[i]
        rssi_filtered[i-offset] = rssi[i]

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
rssi_ticks = [-100, -80, -60, -40]

# What size does the figure need to be in inches to fit the image?
fig.set_figheight(height / float(dpi))
fig.set_figwidth(width / float(dpi))

norm = matplotlib.colors.Normalize(vmin=rssi_ticks[0], vmax=rssi_ticks[-1]) 

normed_rssi = norm.__call__(rssi)

sc = ax.scatter(longitude_filtered, latitude_filtered, zorder=1, alpha= 0.7, c=rssi_filtered, norm=norm, cmap='RdYlGn', s=30)
ax.set_xlabel("longitude")
ax.set_ylabel("latitude")
# create a scalarmappable from the colormap
sm = matplotlib.cm.ScalarMappable(cmap='RdYlGn', norm=norm)    
sm.set_array([])
cax = fig.add_axes([ax.get_position().x1+0.01,ax.get_position().y0,0.02,ax.get_position().height])  
cbar = fig.colorbar(sm, ticks=rssi_ticks, aspect=10, orientation='vertical', ax=ax, label='RSSI', cax=cax)  

if(write_tex):

    tikzplotlib.save(str(Path(__file__).parent) + "/figures/%s.tex" % save_name, encoding="utf-8")

    # post processing tex file

    reading_file = open(str(Path(__file__).parent) + "/figures/%s.tex" % save_name, "r")

    # prepare tick labels

    rssi_ticks_str = ""

    for i in range(len(rssi_ticks)):
        rssi_ticks_str += "%.1f" % rssi_ticks[i]

        if(i != len(rssi_ticks)-1):
            rssi_ticks_str += ", "


    color_bar = [
        "yticklabel style={/pgf/number format/fixed,/pgf/number format/precision=3},",
        "xticklabel style={/pgf/number format/fixed,/pgf/number format/precision=3, rotate=90},",
        "point meta min=%.1f, point meta max=%.1f," % (rssi_ticks[0], rssi_ticks[-1]),
        "colormap={custom}{[1pt]",
        "rgb(0pt)=(0.647058823529412,0,0.149019607843137);",
        "rgb(1pt)=(0.843137254901961,0.188235294117647,0.152941176470588);",
        "rgb(2pt)=(0.956862745098039,0.427450980392157,0.262745098039216);",
        "rgb(3pt)=(0.992156862745098,0.682352941176471,0.380392156862745);",
        "rgb(4pt)=(0.996078431372549,0.87843137254902,0.545098039215686);",
        "rgb(5pt)=(1,1,0.749019607843137);",
        "rgb(6pt)=(0.850980392156863,0.937254901960784,0.545098039215686);",
        "rgb(7pt)=(0.650980392156863,0.850980392156863,0.415686274509804);",
        "rgb(8pt)=(0.4,0.741176470588235,0.388235294117647);",
        "rgb(9pt)=(0.101960784313725,0.596078431372549,0.313725490196078);",
        "rgb(10pt)=(0,0.407843137254902,0.215686274509804)",
        "},",
        "colorbar,",
        "colorbar style={",
        "        ylabel=$RSSI$ in dBm,",
        "        ytick={%s}," % rssi_ticks_str,
        "        yticklabel style={",
        "            text width=2.5em,",
        "            align=right,",
        "            /pgf/number format/fixed,/pgf/number format/precision=3",
        "        }",
        "    }"
    ]
    stage = 0
    new_file_content = ""
    for line in reading_file:
        stripped_line = line.strip()

        new_line = stripped_line

        if(stage == 0 and stripped_line.startswith("ytick style={color=black}")):
            new_file_content += stripped_line +",\n"
            for s in color_bar:
                new_file_content += s +"\n"
            stage = 1

        elif(stripped_line.__contains__("%s-000.png" % save_name)):
            new_line = stripped_line.replace("%s-000.png" % save_name, "figures/tikz/%s-000.png" % save_name)
            new_file_content += new_line +"\n"

        elif(stage == 1 and stripped_line.startswith(r"\end{axis}")):
            new_file_content += new_line +"\n"
            new_file_content += "\n"
            new_file_content += "\end{tikzpicture}"
            new_file_content += "\n"
            break
        
        else:
            new_file_content += new_line +"\n"

    reading_file.close()

    writing_file = open(str(Path(__file__).parent) + "/figures/%s.tex" % save_name, "w")
    writing_file.write(new_file_content)
    writing_file.close()

ax.set_title('Plotting GPS data')
plt.show()