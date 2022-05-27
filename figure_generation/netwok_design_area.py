import numpy as np
import matplotlib.pyplot as plt
import math
import tikzplotlib
from pathlib import Path

# return air_time in ms
def get_airtime(SF, band, n_pay, n_pre, CR) -> float:

    symbol_duration = (2**SF) / (band)
    return (n_pre + 4.25 + 8 + math.ceil( (8*n_pay - 4*SF +28)/(4*SF) )*(CR+4) )* symbol_duration


if __name__ == "__main__":

    SF = 7
    n_pay = 26
    n_pre = 12
    band = 125000
    CR = 1

    air_time_7 = get_airtime(SF, band, n_pay, n_pre, CR)
    air_time_8 = get_airtime(8, band, n_pay, n_pre, CR)
    air_time_10 = get_airtime(10, band, n_pay, n_pre, CR)

    print(air_time_7)

    air_time_minute_7 = air_time_7 / 60
    air_time_minute_8 = air_time_8 / 60
    air_time_minute_10 = air_time_10 / 60


    t_mon = np.linspace(0, 20, 201)
    print(t_mon)

    n_nodes_calc_7 = np.floor( (t_mon * 0.01) / air_time_minute_7 )
    n_nodes_calc_8 =  np.floor( (t_mon * 0.01) / air_time_minute_8 )
    n_nodes_calc_10 =  np.floor( (t_mon * 0.01) / air_time_minute_10 )

    draw_st = "steps-post"
    draw_st = "default"

    f, ax = plt.subplots(1, 1)
    ax.plot(t_mon, n_nodes_calc_7, drawstyle=draw_st)
    ax.plot(t_mon, n_nodes_calc_8, drawstyle=draw_st)
    ax.plot(t_mon, n_nodes_calc_10, drawstyle=draw_st)
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 200)
    ax.set_xlabel(r"$T_\mathrm{mon}$ in min")
    ax.set_ylabel(r"$N_\mathrm{max}$")

    if(draw_st == "steps-post"):
        ax.fill_between(t_mon, n_nodes_calc_7, step="post", alpha=0.4)
        ax.fill_between(t_mon, n_nodes_calc_8, step="post", alpha=0.4)
        ax.fill_between(t_mon, n_nodes_calc_10, step="post", alpha=0.4)
    else:
        ax.fill_between(t_mon, n_nodes_calc_7, alpha=0.4)
        ax.fill_between(t_mon, n_nodes_calc_8, alpha=0.4)
        ax.fill_between(t_mon, n_nodes_calc_10, alpha=0.4)

    ax.legend(["SF = 7", "SF = 8", "SF = 10"])

    print(n_nodes_calc_7[-1])
    print(n_nodes_calc_8[-1])
    print(n_nodes_calc_10[-1])

    tikzplotlib.save(str(Path(__file__).parent) + "/figures/network_design_area.tex", encoding="utf-8")

    plt.show()
