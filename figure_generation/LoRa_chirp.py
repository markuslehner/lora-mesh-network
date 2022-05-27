import matplotlib.pyplot as plt
from pathlib import Path
from lib import LoRa, LoRa_plot
import tikzplotlib

Br = 20e3      # Bandbreite des ausgesendeten Down-Chirps [Hz]
fs = 100e3        # Abtastfrequenz [Hz]
Tp = 1e-3      # Dauer des Up-Chirps [s]

time_vector = LoRa.get_time(Tp, fs, include_last=True)
chirp_time = LoRa.get_chirp(Br, Tp, fs, 0, Br/2, include_last=True)
chirp_freq = LoRa.get_frequency(Br, Tp, fs, 0, Br/2, include_last=True)

print(time_vector[1])

LoRa_plot.plot_time_spectrogram_analytical(chirp_time, chirp_freq, time_vector, Br/2, Br, 1, "Chirp")

tikzplotlib.save(str(Path(__file__).parent) + "/figures/LoRa_chirp.tex")

plt.show()