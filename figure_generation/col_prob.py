import numpy as np
import matplotlib.pyplot as plt
import tikzplotlib
from pathlib import Path

def p_col(time, n):
    return (1-(n-1)*time)**n


if __name__ == "__main__":

    time = np.linspace(0, 0.25, 251)

    col_two = p_col(time, 2)
    col_three = p_col(time, 3)
    col_four = p_col(time, 4)

    f, ax = plt.subplots(1, 1)
    ax.plot(time, col_two)
    ax.plot(time, col_three)
    ax.plot(time, col_four)
    # ax.set_ylim(0, 1)
    # ax.set_xlim(0, 0.25)
    ax.set_ylabel(r"$P(\mathrm{No \ collision})$")
    ax.set_xlabel(r"$\omega$")

    ax.legend([r"$n = 2$", r"$n = 3$", r"$n = 4$"])

    tikzplotlib.save(str(Path(__file__).parent) + "/figures/collision_probability.tex")

    plt.show()