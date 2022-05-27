import numpy as np
import matplotlib.pyplot as plt
import tikzplotlib

plot_dist_min = 0
plot_dist_max = 3000

min_dist = 500
max_dist = 2500
decay = [1, 2, 0.5]
error_rate = 0.05

dist = np.linspace(min_dist, max_dist, 1001)

dist_before = np.linspace(plot_dist_min, min_dist, 101)
dist_after = np.linspace(max_dist, plot_dist_max, 101)

start_exp = np.log(error_rate)

fact = ( (dist-min_dist) / (max_dist - min_dist) )

f, ax = plt.subplots(1, 1)
labels = []
for dec in decay:

    prob = np.concatenate(( 1 - np.ones((len(dist_before)))*error_rate, 1 - np.exp(start_exp*(1 - fact**dec) ), np.zeros((len(dist_after)))), axis=0)
    d = np.concatenate((dist_before, dist, dist_after), axis=0)
    ax.plot(d, prob)
    labels.append("$%s = %.1f$" % (r"\eta", dec))

ax.set_ylabel(r"$P_\mathrm{succ}(d)$")
ax.set_xlabel(r"$d$ in m")
ax.grid()
ax.legend(labels)

tikzplotlib.save("figures/transmission_error.tex", encoding="utf-8")

# post processing
reading_file = open("figures/transmission_error.tex", "r")

new_file_content = ""
stage = 0
for line in reading_file:
    stripped_line = line.strip()
    new_line = stripped_line

    # logic for replacing goes here
    if(stage == 0 and stripped_line.startswith(r"tick pos=left,")):
        stage += 1
        new_line += "\nxtick={0,500,1000,1500,2000,2500,3000},\n"
        new_line += "xticklabels={0,$r_\mathrm{min}$,,,,$r_\mathrm{max}$,},"
    elif(stage == 1 and stripped_line.startswith(r"xmin")):
        new_line = "xmin=0, xmax=3000,"
    elif(stage == 1 and stripped_line.startswith(r"ymin")):
        new_line = "ymin=-0.05, ymax=1.0,"

    new_file_content += new_line +"\n"

reading_file.close()

writing_file = open("figures/transmission_error.tex", "w")
writing_file.write(new_file_content)
writing_file.close()

ax.set_xticks([0, 500, 2500, 3000])
ax.set_xticklabels(["0", "min", "max", ""])
ax.set_xlim((0, 3000))

plt.show()