import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from lib import LoRa, LoRa_plot
from bitarray import bitarray
from bitarray.util import ba2int
import tikzplotlib

SF = 7
CR = 1

bit_data = bitarray('00000001100101101011101010001010100')

data = 95
win_size = 1024*0.5

Br = 125e3          # Bandbreite des ausgesendeten Down-Chirps [Hz]
fs = 250e3          # Abtastfrequenz [Hz]
# Tp = 1e-3         # Dauer des Up-Chirps [s]
Tp = 2**SF/Br

fc = Br/2

print("Abtastintervall: %.2f ms" % (1/fs*1e6) )   # Abtastintervall in Entfernungsrichtung [s]
print("Chirprate kr: %.2f MHz/s" % (Br/Tp/1e6) )

print("T_symbol: %.3f ms" % (Tp * 1e3) )
print("R_b: %.3f" % (Br/2**SF*SF) )
print("R_b_code: %.3f" % (SF* (4/(4+CR))/(2**SF/Br) ) )

sr = LoRa.get_chirp(Br, Tp, fs, 0, fc, include_last=True)
sr_ref = LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=True)
sr_ref_start = LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=False)
sr_symbol = LoRa.get_chirp(Br, Tp, fs, data / 2**SF, fc, include_last=True)
tau = LoRa.get_time(Tp, fs, include_last=True)

# generate signal from bit data
num_zeros = int(SF - len(bit_data)% SF) if len(bit_data)% SF > 0 else 0
print("appending %i zeros" % num_zeros)
for i in range( num_zeros ):
    bit_data.append(0)

time_signal = np.zeros((0))
freq_signal = np.zeros((0))
data_signal = np.zeros((0))

# calculate data and encode in chirp
print("number of chirps: %.2f" % (len(bit_data)/SF) )

for i in range(int(len(bit_data)/SF)):
    # slice bit array
    data = ba2int(bit_data[i*SF:(i+1)*SF])
    print("data %i: %i" % (i, data))

    last = i == int(len(bit_data)/SF)-1

    time_signal = np.concatenate(( time_signal, LoRa.get_chirp(Br, Tp, fs, data / 2**SF, fc, include_last=last) ))
    freq_signal = np.concatenate(( freq_signal, LoRa.get_frequency(Br, Tp, fs, data / 2**SF, fc, include_last=last) ))
    data_signal = np.concatenate(( data_signal, np.ones((len(sr_ref_start)+last))*data )) 

time_vector = LoRa.get_time( (len(time_signal)-1)/len(sr_ref_start) * Tp, fs, include_last=True)

print(time_vector[-1])
print(len(time_vector))

LoRa_plot.plot_data_frequency(freq_signal, data_signal, time_vector*1e3, int(len(bit_data)/SF), Tp*1e3, fc, Br, SF, bit_data, 4, "Signal")

tikzplotlib.save(str(Path(__file__).parent) +  "/figures/LoRa_data.tex")

plt.show()