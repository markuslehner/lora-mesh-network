import numpy as np
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path

nodes = [1, 3, 7]

bat = np.load(str(Path(__file__).parent.parent) +  "/simulation/results/battery_logs.npy")
time = np.linspace(0, np.shape(bat)[1]*1, np.shape(bat)[1]-1)

f, ax = plt.subplots(1, 1)
labels = []
for i in range(np.shape(bat)[0]):

    ax.plot(time, bat[i,:-1])
    labels.append("node %i" % nodes[i])

ax.set_ylabel(r"$C_\mathrm{bat}(t)$")
ax.set_xlabel(r"$t$ in min")
ax.grid()
ax.legend(labels)

tikzplotlib.save("figures/battery_level.tex", encoding="utf-8")

plt.show()