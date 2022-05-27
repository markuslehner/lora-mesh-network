import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path

# load files
prefix = "double_SF7"

scenarios = ["real", "flooding"]

err_rate = "0.05"

num = 10

num_nodes = 14

# save files
suffix = prefix

pdr = np.zeros((len(scenarios), num, num_nodes))
collision_rate = np.zeros((len(scenarios), num, num_nodes))
tx_at_node = np.zeros((len(scenarios), num, num_nodes))

for s in range(len(scenarios)):
    for i in range(num):
        try:
            file = str(Path(__file__).parent) + '\\simulation\\results\\%s_%s_%s_%i_res.csv' % (prefix, scenarios[s], err_rate[2:], i)
            data = pd.read_csv(file, delimiter=";" ) 
            
            nodes_names = data.columns.values.tolist()[2:]
            received = data.iloc[4,:].values[2:]
            request = data.iloc[5,:].values[2:]
            sent = data.iloc[6,:].values[2:]
            
            if(np.sum(received) <= np.sum(sent)):
                pdr[s, i, :] = received/sent
            else:
                pdr[s, i, :] = 1.0

            collisions = data.iloc[7,:].values[2:]
            total_rx = data.iloc[10,:].values[2:]

            collision_rate[s, i, :] = collisions/total_rx
            tx_at_node[s, i, :] = total_rx
        except Exception as ex:
            print("Encountered error with file: %s" % file)
            raise ex

f, ax = plt.subplots(2, 1)
ax[0].boxplot(np.squeeze(pdr[0,:,:]))
ax[0].set_title(r"\textbf{network}")
ax[0].set_xticklabels([])
ax[1].boxplot(np.squeeze(pdr[1,:,:]))
ax[1].set_title(r"\textbf{flooding}")
ax[1].set_xticklabels(nodes_names)
ax[1].set_xlabel(r"$P_\mathrm{c,static}$")

tikzplotlib.save(str(Path(__file__).parent) + "/figures/packet_delivery_ratio_node_%s.tex" % suffix, encoding="utf-8")
f.suptitle("Packet delivery ratio")

f, ax = plt.subplots(2, 1)
ax[0].boxplot(np.squeeze(collision_rate[0,:,:]))
ax[0].set_title(r"\textbf{network}")
ax[0].set_xticklabels([])
ax[1].boxplot(np.squeeze(collision_rate[1,:,:]))
ax[1].set_title(r"\textbf{flooding}")
ax[1].set_xticklabels(nodes_names)
ax[1].set_xlabel(r"$P_\mathrm{c,static}$")

tikzplotlib.save(str(Path(__file__).parent) + "/figures/collisions_node_%s.tex" % suffix, encoding="utf-8")
f.suptitle("Overall collision rate")

# calc max transmissions
t_air = 56 if prefix.endswith("SF7") else 404
max_trans = 864000 / t_air

f, ax = plt.subplots(2, 1)
ax[0].boxplot(np.squeeze(tx_at_node[0,:,:]))
ax[0].set_title(r"\textbf{network}")
ax[0].set_xticklabels([])
#ax[0].axhline(max_trans)
ax[1].boxplot(np.squeeze(tx_at_node[1,:,:]))
ax[1].set_title(r"\textbf{flooding}")
#ax[1].axhline(max_trans)
ax[1].set_xticklabels(nodes_names)
ax[1].set_xlabel(r"$P_\mathrm{c,static}$")

tikzplotlib.save(str(Path(__file__).parent) + "/figures/packets_sent_node_%s.tex" % suffix, encoding="utf-8")
f.suptitle("Total number of packets sent")

# post processing
# add y axis labels
# create combination plot

# static text
comb_start = [
    "% This file was created with tikzplotlib v0.9.15.",
    "% Post processing done automatically by script simulation_results.py",
    r"\begin{tikzpicture}",
    "",
    "\definecolor{color0}{rgb}{1,0.498039215686275,0.0549019607843137}",
    "\definecolor{color1}{rgb}{0.12156862745098,0.466666666666667,0.705882352941177}",
    "",
    r"\begin{groupplot}[group style={group size=1 by 6}]",
    ""
]

labels = [
    "$PDR$",
    "$\gamma_\mathrm{col}$",
    "$n_\mathrm{air}$"
]

files = [
    str(Path(__file__).parent) + "/figures/packet_delivery_ratio_node_%s.tex" % suffix,
    str(Path(__file__).parent) + "/figures/collisions_node_%s.tex" % suffix,
    str(Path(__file__).parent) + "/figures/packets_sent_node_%s.tex" % suffix
]

# variables
combination = ""

for i in range(len(comb_start)):
    combination += comb_start[i] + "\n"

for i in range(3):
    reading_file = open(files[i], "r")

    new_file_content = ""
    stage = 0
    for line in reading_file:
        stripped_line = line.strip()
        new_line = stripped_line

        # logic for replacing goes here
        if(stage == 0 and stripped_line.startswith(r"\nextgroupplot")):
            stage += 1
        elif(stripped_line.startswith("ytick style={color=black}")):
            if(stage == 1):
                if(i > 0):
                    combination += "yshift=-1cm,\n"
                new_line += ",\nxtick={%s},\n" % str([i for i in range(1, num_nodes)])[1:-1]
                new_line += "xticklabels={,,,},"
            elif(stage == 2):
                new_line += ",\nylabel={%s},\n" % labels[i]
                new_line += "ylabel absolute,\n"
                new_line += "xticklabel style={rotate=90},\n"
                new_line += "every axis y label/.style={at={(axis description cs:-0.15,1.27)},rotate=90,anchor=center},"

            
            stage += 1
        elif(stage == 3 and stripped_line.startswith("\end{groupplot}")):
            stage += 1

        new_file_content += new_line +"\n"
        if(stage > 0 and stage < 4):
            combination += new_line +"\n"

    reading_file.close()

    writing_file = open(files[i], "w")
    writing_file.write(new_file_content)
    writing_file.close()


# end of file
combination += "\end{groupplot}\n\n\end{tikzpicture}\n"

writing_file = open(str(Path(__file__).parent) + "/figures/combination_node_%s.tex" % suffix, "w")
writing_file.write(combination)
writing_file.close()

plt.show()